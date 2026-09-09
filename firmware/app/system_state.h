#ifndef SYSTEM_STATE_H
#define SYSTEM_STATE_H

#include <stdbool.h>

typedef enum {
    SYSTEM_STATE_INIT = 0,
    SYSTEM_STATE_DISABLED,
    SYSTEM_STATE_ARMED,
    SYSTEM_STATE_RUNNING,
    SYSTEM_STATE_FAULT
} SystemState_t;

void SystemState_Init(void);
SystemState_t SystemState_Get(void);
bool SystemState_RequestArmed(bool safety_satisfied, bool estop_released, bool no_active_faults, bool sensors_valid, float current_motor_cmd);
bool SystemState_RequestRunning(void);
void SystemState_RequestDisabled(void);
void SystemState_TriggerFault(void);

#endif
