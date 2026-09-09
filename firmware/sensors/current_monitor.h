#ifndef CURRENT_MONITOR_H
#define CURRENT_MONITOR_H

#include <stdint.h>

typedef struct {
    float offset_voltage;
    float sensitivity_v_per_a;
    float adc_reference_voltage;
    uint32_t adc_resolution_bits;
    float alpha_filter; // low-pass filter coefficient (0.0 to 1.0)
} CurrentMonitorConfig_t;

typedef struct {
    CurrentMonitorConfig_t config;
    float filtered_current;
} CurrentMonitor_t;

void CurrentMonitor_Init(CurrentMonitor_t* monitor, CurrentMonitorConfig_t config);
float CurrentMonitor_ProcessADC(CurrentMonitor_t* monitor, uint32_t adc_counts);

#endif
