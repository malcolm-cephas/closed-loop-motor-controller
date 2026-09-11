/*******************************************************************************
 * @file    control_loop.h
 * @brief   Control loop integration — ties together all subsystems at 100 Hz.
 *
 * This module is called from the TIM6 ISR and orchestrates:
 *   1. Sensor acquisition
 *   2. Speed estimation
 *   3. Current monitoring
 *   4. Fault evaluation
 *   5. PI controller calculation
 *   6. Safety layer enforcement
 *   7. Motor command update
 *   8. Telemetry sample storage
 ******************************************************************************/
#ifndef CONTROL_LOOP_H
#define CONTROL_LOOP_H

#include <stdbool.h>

void ControlLoop_Init(void);
void ControlLoop_Execute(void);  /* Called from timer ISR */
void ControlLoop_SetTargetRPM(float rpm);
float ControlLoop_GetTargetRPM(void);
bool ControlLoop_IsMotorOutputEnabled(void);

#endif /* CONTROL_LOOP_H */
