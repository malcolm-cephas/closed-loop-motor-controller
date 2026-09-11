/*******************************************************************************
 * @file    control_loop.c
 * @brief   Control loop integration implementation.
 *
 * PHASE 3 STATUS: Motor output is PERMANENTLY DISABLED.
 * This module runs the full control pipeline but forces the motor command
 * to zero for safe hardware bring-up and peripheral validation.
 ******************************************************************************/

#include "control_loop.h"
#include "system_state.h"
#include "../control/pi_controller.h"
#include "../control/speed_estimator.h"
#include "../sensors/current_monitor.h"
#include "../safety/fault_manager.h"
#include "../safety/safety_layer.h"
#include "../drivers/motor_driver.h"
#include "../drivers/encoder_driver.h"
#include "../communication/telemetry_format.h"
#include "../diagnostics/timing_diag.h"
#include "../bsp/bsp.h"
#include "../bsp/bsp_config.h"

/* ---- Configuration ---- */
#define CONTROL_DT              0.01f   /* 10 ms sample period */

/*
 * Encoder counts per output revolution.
 * THIS VALUE IS A PROVISIONAL ASSUMPTION AND MUST BE VERIFIED EXPERIMENTALLY.
 * Assumed: 11 PPR motor * 34:1 gearbox * 4x decoding = 1496.
 */
#define PROVISIONAL_COUNTS_PER_REV  1496.0f

/* ---- Module State ---- */
static PI_Controller_t    _pi;
static SpeedEstimator_t   _speed_est;
static CurrentMonitor_t   _current_mon;
static TimingDiag_t       _timing;
static float              _target_rpm = 0.0f;

/* Latest telemetry sample (written by ISR, read by main loop) */
static volatile TelemetryData_t _latest_telemetry;
static volatile uint32_t _tick_count = 0;

void ControlLoop_Init(void) {
    /* PI Controller — simulation-tuned starting gains */
    PI_Config_t pi_cfg = {
        .kp      = 1.0f,
        .ki      = 10.0f,
        .out_max = 100.0f,
        .out_min = -100.0f
    };
    PI_Init(&_pi, pi_cfg);

    /* Speed Estimator — PROVISIONAL encoder configuration */
    SpeedEstimatorConfig_t se_cfg = {
        .counts_per_output_revolution = PROVISIONAL_COUNTS_PER_REV
    };
    SpeedEstimator_Init(&_speed_est, se_cfg);

    /* Current Monitor — PROVISIONAL calibration for INA169.
     * These values MUST be experimentally calibrated. */
    CurrentMonitorConfig_t cm_cfg = {
        .offset_voltage      = 0.0f,   /* INA169 is ground-referenced */
        .sensitivity_v_per_a = 0.5f,   /* Needs verification with actual module */
        .adc_reference_voltage = BSP_ADC_VREF,
        .adc_resolution_bits = BSP_ADC_RESOLUTION,
        .alpha_filter        = 0.2f
    };
    CurrentMonitor_Init(&_current_mon, cm_cfg);

    /* Safety Layer */
    SafetyConfig_t safety_cfg = {
        .max_motor_command = 100.0f,
        .max_slew_rate     = 500.0f  /* %/sec — generous for initial testing */
    };
    SafetyLayer_Init(safety_cfg);

    /* Timing Diagnostics */
    TimingDiag_Init(&_timing, BSP_HCLK_HZ);

    _target_rpm = 0.0f;
    _tick_count = 0;
}

void ControlLoop_Execute(void) {
    TimingDiag_MarkStart(&_timing);

    /* 1. Acquire encoder count */
    int32_t enc_count = EncoderDriver_GetCount();

    /* 2. Estimate speed */
    float measured_rpm = SpeedEstimator_CalculateRPM_CountBased(
        &_speed_est, enc_count, CONTROL_DT);

    /* 3. Acquire current */
    uint32_t adc_raw = BSP_ADC_ReadRaw();
    float current_amps = CurrentMonitor_ProcessADC(&_current_mon, adc_raw);

    /* 4. Evaluate faults (placeholder thresholds — MUST be tuned to real hardware) */
    /* Overcurrent check */
    if (current_amps > 1.8f) {
        FaultManager_SetFault(FAULT_OVERCURRENT);
    }
    /* E-stop check (polled in addition to EXTI for redundancy) */
    if (BSP_EStop_IsPressed()) {
        FaultManager_SetFault(FAULT_ESTOP);
    }

    /* 5. Compute PI controller output */
    float pi_output = 0.0f;
    if (SystemState_Get() == SYSTEM_STATE_RUNNING) {
        pi_output = PI_Calculate(&_pi, _target_rpm, measured_rpm, CONTROL_DT);
    }

    /* 6. Pass through safety layer */
    float safe_command = SafetyLayer_ProcessCommand(pi_output, CONTROL_DT);

    /* 7. Update motor command
     * PHASE 3: Motor output is DISABLED. The safe_command is calculated
     * but NOT applied. This is intentional for hardware bring-up. */
    /* MotorDriver_SetDuty(safe_command); */  /* UNCOMMENT IN PHASE 4 */
    (void)safe_command;  /* Suppress unused warning */

    /* 8. Store telemetry sample */
    _tick_count++;
    _latest_telemetry.timestamp_ms  = _tick_count * 10;  /* 10 ms per tick */
    _latest_telemetry.target_rpm    = _target_rpm;
    _latest_telemetry.measured_rpm  = measured_rpm;
    _latest_telemetry.error_rpm     = _target_rpm - measured_rpm;
    _latest_telemetry.control_output = safe_command;
    _latest_telemetry.current_amps  = current_amps;
    _latest_telemetry.system_state  = (uint8_t)SystemState_Get();
    _latest_telemetry.active_faults = FaultManager_GetActiveFaults();

    TimingDiag_MarkEnd(&_timing);
}

void ControlLoop_SetTargetRPM(float rpm) {
    _target_rpm = rpm;
}

float ControlLoop_GetTargetRPM(void) {
    return _target_rpm;
}

bool ControlLoop_IsMotorOutputEnabled(void) {
    return false;  /* PHASE 3: Always false */
}
