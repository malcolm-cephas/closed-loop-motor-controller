#ifndef FAULT_MANAGER_H
#define FAULT_MANAGER_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    FAULT_NONE          = 0,
    FAULT_ESTOP         = (1 << 0),
    FAULT_OVERCURRENT   = (1 << 1),
    FAULT_OVERSPEED     = (1 << 2),
    FAULT_STALL         = (1 << 3),
    FAULT_ENCODER       = (1 << 4),
    FAULT_SENSOR        = (1 << 5),
    FAULT_DRIVER        = (1 << 6),
    FAULT_WATCHDOG      = (1 << 7)
} FaultType_t;

void FaultManager_Init(void);
void FaultManager_SetFault(FaultType_t fault);
void FaultManager_ClearFault(FaultType_t fault);
void FaultManager_ClearAll(void);
uint32_t FaultManager_GetActiveFaults(void);
bool FaultManager_HasActiveFault(void);

#endif
