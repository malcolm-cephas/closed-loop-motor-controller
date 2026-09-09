#ifndef TELEMETRY_FORMAT_H
#define TELEMETRY_FORMAT_H

#include <stdint.h>

typedef struct {
    uint32_t timestamp_ms;
    float target_rpm;
    float measured_rpm;
    float error_rpm;
    float control_output;
    float current_amps;
    uint8_t system_state; // maps to SystemState_t
    uint32_t active_faults; // maps to FaultManager active_faults
} TelemetryData_t;

#endif
