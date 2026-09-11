/*******************************************************************************
 * @file    timing_diag.h
 * @brief   Control loop timing diagnostics — measures execution time and jitter
 *          using the DWT cycle counter.
 ******************************************************************************/
#ifndef TIMING_DIAG_H
#define TIMING_DIAG_H

#include <stdint.h>

typedef struct {
    uint32_t last_cycles;
    uint32_t min_cycles;
    uint32_t max_cycles;
    uint64_t total_cycles;
    uint32_t sample_count;
    uint32_t cpu_freq_hz;
} TimingDiag_t;

void TimingDiag_Init(TimingDiag_t* td, uint32_t cpu_freq_hz);
void TimingDiag_MarkStart(TimingDiag_t* td);
void TimingDiag_MarkEnd(TimingDiag_t* td);

float TimingDiag_GetLastUs(const TimingDiag_t* td);
float TimingDiag_GetMinUs(const TimingDiag_t* td);
float TimingDiag_GetMaxUs(const TimingDiag_t* td);
float TimingDiag_GetAvgUs(const TimingDiag_t* td);

#endif /* TIMING_DIAG_H */
