#include "fault_manager.h"
#include "../app/system_state.h"

static uint32_t active_faults = 0;

void FaultManager_Init(void) {
    active_faults = 0;
}

void FaultManager_SetFault(FaultType_t fault) {
    active_faults |= fault;
    SystemState_TriggerFault();
}

void FaultManager_ClearFault(FaultType_t fault) {
    active_faults &= ~fault;
}

void FaultManager_ClearAll(void) {
    active_faults = 0;
}

uint32_t FaultManager_GetActiveFaults(void) {
    return active_faults;
}

bool FaultManager_HasActiveFault(void) {
    return (active_faults != 0);
}
