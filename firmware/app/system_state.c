#include "system_state.h"

static SystemState_t current_state = SYSTEM_STATE_INIT;

void SystemState_Init(void) {
    current_state = SYSTEM_STATE_INIT;
}

SystemState_t SystemState_Get(void) {
    return current_state;
}

bool SystemState_RequestArmed(bool safety_satisfied, bool estop_released, bool no_active_faults, bool sensors_valid, float current_motor_cmd) {
    if (current_state == SYSTEM_STATE_DISABLED) {
        if (safety_satisfied && estop_released && no_active_faults && sensors_valid && (current_motor_cmd == 0.0f)) {
            current_state = SYSTEM_STATE_ARMED;
            return true;
        }
    }
    return false;
}

bool SystemState_RequestRunning(void) {
    if (current_state == SYSTEM_STATE_ARMED) {
        current_state = SYSTEM_STATE_RUNNING;
        return true;
    }
    return false;
}

void SystemState_RequestDisabled(void) {
    if (current_state != SYSTEM_STATE_FAULT) {
        current_state = SYSTEM_STATE_DISABLED;
    }
}

void SystemState_TriggerFault(void) {
    current_state = SYSTEM_STATE_FAULT;
}
