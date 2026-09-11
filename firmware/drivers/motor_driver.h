/*******************************************************************************
 * @file    motor_driver.h
 * @brief   Motor driver interface — abstraction over BSP PWM and enable pins.
 *
 * All motor output commands MUST pass through the safety layer before
 * reaching this driver. The PI controller never calls this directly.
 ******************************************************************************/
#ifndef MOTOR_DRIVER_H
#define MOTOR_DRIVER_H

#include <stdbool.h>

void MotorDriver_Init(void);
void MotorDriver_Enable(void);
void MotorDriver_Disable(void);
void MotorDriver_SetDuty(float duty_percent);  /* 0.0 to 100.0 */
bool MotorDriver_IsEnabled(void);

#endif /* MOTOR_DRIVER_H */
