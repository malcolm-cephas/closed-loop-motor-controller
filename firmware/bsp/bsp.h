/*******************************************************************************
 * @file    bsp.h
 * @brief   Board Support Package — Hardware initialization and access layer
 *          for NUCLEO-G431RB.
 *
 * This module is the ONLY layer permitted to call STM32 HAL functions directly.
 * All other firmware modules access hardware through the driver interfaces.
 ******************************************************************************/
#ifndef BSP_H
#define BSP_H

#include <stdint.h>
#include <stdbool.h>

/* ---- System Init ---- */
void BSP_SystemClock_Config(void);
void BSP_Init(void);

/* ---- PWM (TIM1_CH1, PA8) ---- */
void BSP_PWM_Init(void);
void BSP_PWM_Enable(void);
void BSP_PWM_Disable(void);
void BSP_PWM_SetDuty(float duty_percent);  /* 0.0 to 100.0 */

/* ---- Motor Driver Enable (BTS7960 R_EN/L_EN) ---- */
void BSP_DriverEnable_Init(void);
void BSP_DriverEnable_Set(bool enabled);

/* ---- Encoder (TIM2 Encoder Mode, PA0/PA1) ---- */
void BSP_Encoder_Init(void);
int32_t BSP_Encoder_GetCount(void);
void BSP_Encoder_Reset(void);

/* ---- ADC / Current Sensor (ADC2_IN17, PA4) ---- */
void BSP_ADC_Init(void);
uint32_t BSP_ADC_ReadRaw(void);

/* ---- UART / Telemetry (LPUART1, PA2/PA3) ---- */
void BSP_UART_Init(void);
void BSP_UART_Transmit(const uint8_t* data, uint16_t length);
bool BSP_UART_TransmitReady(void);

/* ---- E-Stop (PC13, EXTI) ---- */
void BSP_EStop_Init(void);
bool BSP_EStop_IsPressed(void);

/* ---- Status LED (PA5) ---- */
void BSP_LED_Init(void);
void BSP_LED_Toggle(void);
void BSP_LED_Set(bool on);

/* ---- Control Loop Timer (TIM6, 100 Hz) ---- */
void BSP_ControlTimer_Init(void);

/* ---- Watchdog (IWDG) ---- */
void BSP_Watchdog_Init(void);
void BSP_Watchdog_Refresh(void);

/* ---- Timing Measurement (DWT Cycle Counter) ---- */
void BSP_CycleCounter_Init(void);
uint32_t BSP_CycleCounter_Get(void);

#endif /* BSP_H */
