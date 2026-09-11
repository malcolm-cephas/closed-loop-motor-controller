/*******************************************************************************
 * @file    uart_telemetry.h
 * @brief   UART telemetry serialization — converts TelemetryData_t to
 *          ASCII CSV for transmission. Hardware-independent interface.
 ******************************************************************************/
#ifndef UART_TELEMETRY_H
#define UART_TELEMETRY_H

#include "../communication/telemetry_format.h"
#include <stdint.h>

/* Serialize a telemetry sample to a human-readable ASCII CSV line.
 * Returns the number of bytes written to the buffer. */
uint16_t Telemetry_SerializeCSV(const TelemetryData_t* data, uint8_t* buffer, uint16_t max_len);

#endif /* UART_TELEMETRY_H */
