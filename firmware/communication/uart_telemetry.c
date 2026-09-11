/*******************************************************************************
 * @file    uart_telemetry.c
 * @brief   Telemetry serialization to ASCII CSV.
 ******************************************************************************/

#include "uart_telemetry.h"
#include <stdio.h>

uint16_t Telemetry_SerializeCSV(const TelemetryData_t* data, uint8_t* buffer, uint16_t max_len) {
    int len = snprintf((char*)buffer, max_len,
        "%lu,%.1f,%.1f,%.1f,%.1f,%.3f,%u,%lu\r\n",
        (unsigned long)data->timestamp_ms,
        data->target_rpm,
        data->measured_rpm,
        data->error_rpm,
        data->control_output,
        data->current_amps,
        (unsigned)data->system_state,
        (unsigned long)data->active_faults);

    return (len > 0 && len < max_len) ? (uint16_t)len : 0;
}
