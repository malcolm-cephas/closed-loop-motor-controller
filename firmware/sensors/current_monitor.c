#include "current_monitor.h"

void CurrentMonitor_Init(CurrentMonitor_t* monitor, CurrentMonitorConfig_t config) {
    monitor->config = config;
    monitor->filtered_current = 0.0f;
}

float CurrentMonitor_ProcessADC(CurrentMonitor_t* monitor, uint32_t adc_counts) {
    float max_counts = (float)((1 << monitor->config.adc_resolution_bits) - 1);
    if (max_counts <= 0.0f) return 0.0f;

    float voltage = ((float)adc_counts / max_counts) * monitor->config.adc_reference_voltage;
    float raw_current = (voltage - monitor->config.offset_voltage) / monitor->config.sensitivity_v_per_a;

    monitor->filtered_current = (monitor->config.alpha_filter * raw_current) + 
                                ((1.0f - monitor->config.alpha_filter) * monitor->filtered_current);

    return monitor->filtered_current;
}
