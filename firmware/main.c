/*******************************************************************************
 * @file    main.c
 * @brief   Application entry point for Closed-Loop Motor Controller.
 *
 * Target: NUCLEO-G431RB (STM32G431RBT6)
 *
 * PHASE 3: Hardware bring-up and peripheral validation.
 *          Motor output is DISABLED. Only peripheral I/O is verified.
 ******************************************************************************/

#include "bsp/bsp.h"
#include "bsp/bsp_config.h"
#include "app/system_state.h"
#include "app/control_loop.h"
#include "safety/fault_manager.h"
#include "drivers/motor_driver.h"
#include "communication/uart_telemetry.h"
#include "communication/telemetry_format.h"
#include "diagnostics/timing_diag.h"

#include <string.h>
#include <stdio.h>

/* ---- Shared state accessed by ISR and main loop ---- */
static volatile uint8_t ctrl_loop_flag = 0;
extern volatile TelemetryData_t _latest_telemetry;
extern TimingDiag_t _timing;

/* ---- Watchdog health tracking ---- */
static volatile uint8_t health_ctrl_loop_ok = 0;
static volatile uint8_t health_main_loop_ok = 0;

/*******************************************************************************
 * TIM6 ISR — Control Loop Tick (100 Hz)
 ******************************************************************************/
void TIM6_DAC_IRQHandler(void) {
    /* Clear the TIM6 update interrupt flag */
    if (__HAL_TIM_GET_FLAG(&((TIM_HandleTypeDef){.Instance = TIM6}), TIM_FLAG_UPDATE)) {
        __HAL_TIM_CLEAR_FLAG(&((TIM_HandleTypeDef){.Instance = TIM6}), TIM_FLAG_UPDATE);
    }

    ControlLoop_Execute();
    ctrl_loop_flag = 1;
    health_ctrl_loop_ok = 1;
}

/*******************************************************************************
 * EXTI15_10 ISR — E-Stop (PC13) and optional Driver Fault (PB14)
 ******************************************************************************/
void EXTI15_10_IRQHandler(void) {
    if (__HAL_GPIO_EXTI_GET_IT(BSP_ESTOP_PIN)) {
        __HAL_GPIO_EXTI_CLEAR_IT(BSP_ESTOP_PIN);
        FaultManager_SetFault(FAULT_ESTOP);
        MotorDriver_Disable();
    }
    if (__HAL_GPIO_EXTI_GET_IT(BSP_DRV_FAULT_PIN)) {
        __HAL_GPIO_EXTI_CLEAR_IT(BSP_DRV_FAULT_PIN);
        FaultManager_SetFault(FAULT_DRIVER);
        MotorDriver_Disable();
    }
}

/*******************************************************************************
 * MAIN
 ******************************************************************************/
int main(void) {
    /* ---- Phase 1: Hardware Init ---- */
    BSP_Init();

    /* ---- Phase 2: Software Init ---- */
    SystemState_Init();
    FaultManager_Init();
    MotorDriver_Init();
    ControlLoop_Init();

    /* Transition from INIT to DISABLED */
    SystemState_RequestDisabled();

    /* Send startup banner over UART */
    const char* banner = "\r\n=== Motor Controller v0.1 (Phase 3: Bring-Up) ===\r\n"
                         "timestamp,target,measured,error,output,current,state,faults\r\n";
    BSP_UART_Transmit((const uint8_t*)banner, (uint16_t)strlen(banner));

    /* ---- Phase 3: Enable Watchdog ----
     * Watchdog is initialized AFTER all peripherals are confirmed working.
     * This prevents a boot loop if a peripheral hangs during init. */
    BSP_Watchdog_Init();

    /* ---- Telemetry buffer ---- */
    uint8_t tx_buf[128];
    uint32_t led_counter = 0;

    /* ---- Main Loop ---- */
    while (1) {
        /* Background: Telemetry transmission (non-blocking relative to ISR) */
        if (ctrl_loop_flag) {
            ctrl_loop_flag = 0;

            /* Copy latest telemetry from ISR-written volatile struct */
            TelemetryData_t telem;
            memcpy(&telem, (const void*)&_latest_telemetry, sizeof(TelemetryData_t));

            /* Serialize and transmit */
            uint16_t len = Telemetry_SerializeCSV(&telem, tx_buf, sizeof(tx_buf));
            if (len > 0 && BSP_UART_TransmitReady()) {
                BSP_UART_Transmit(tx_buf, len);
            }

            /* Heartbeat LED: toggle every 500 ms (50 ticks at 100 Hz) */
            led_counter++;
            if (led_counter >= 50) {
                BSP_LED_Toggle();
                led_counter = 0;
            }

            health_main_loop_ok = 1;
        }

        /* Watchdog: Only refresh if BOTH the control loop AND main loop
         * have executed since the last refresh. This ensures the watchdog
         * detects failures in either path. */
        if (health_ctrl_loop_ok && health_main_loop_ok) {
            BSP_Watchdog_Refresh();
            health_ctrl_loop_ok = 0;
            health_main_loop_ok = 0;
        }
    }
}
