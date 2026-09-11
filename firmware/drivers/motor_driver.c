/*******************************************************************************
 * @file    motor_driver.c
 * @brief   Motor driver implementation — wraps BSP PWM and BTS7960 enable.
 ******************************************************************************/

#include "motor_driver.h"
#include "../bsp/bsp.h"

static bool _enabled = false;

void MotorDriver_Init(void) {
    _enabled = false;
    /* BSP_PWM_Init and BSP_DriverEnable_Init already called by BSP_Init */
}

void MotorDriver_Enable(void) {
    BSP_PWM_SetDuty(0.0f);   /* Ensure 0% before enabling */
    BSP_PWM_Enable();
    BSP_DriverEnable_Set(true);
    _enabled = true;
}

void MotorDriver_Disable(void) {
    BSP_DriverEnable_Set(false);
    BSP_PWM_Disable();
    _enabled = false;
}

void MotorDriver_SetDuty(float duty_percent) {
    if (!_enabled) return;
    BSP_PWM_SetDuty(duty_percent);
}

bool MotorDriver_IsEnabled(void) {
    return _enabled;
}
