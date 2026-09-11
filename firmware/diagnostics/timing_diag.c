/*******************************************************************************
 * @file    timing_diag.c
 * @brief   Timing diagnostics implementation using DWT cycle counter.
 ******************************************************************************/

#include "timing_diag.h"

/* Forward declaration — BSP provides the cycle counter */
extern uint32_t BSP_CycleCounter_Get(void);

static uint32_t _start_count = 0;

void TimingDiag_Init(TimingDiag_t* td, uint32_t cpu_freq_hz) {
    td->last_cycles  = 0;
    td->min_cycles   = 0xFFFFFFFF;
    td->max_cycles   = 0;
    td->total_cycles = 0;
    td->sample_count = 0;
    td->cpu_freq_hz  = cpu_freq_hz;
}

void TimingDiag_MarkStart(TimingDiag_t* td) {
    (void)td;
    _start_count = BSP_CycleCounter_Get();
}

void TimingDiag_MarkEnd(TimingDiag_t* td) {
    uint32_t end_count = BSP_CycleCounter_Get();
    uint32_t elapsed = end_count - _start_count; /* Handles single wrap */

    td->last_cycles = elapsed;
    if (elapsed < td->min_cycles) td->min_cycles = elapsed;
    if (elapsed > td->max_cycles) td->max_cycles = elapsed;
    td->total_cycles += elapsed;
    td->sample_count++;
}

float TimingDiag_GetLastUs(const TimingDiag_t* td) {
    return (float)td->last_cycles / ((float)td->cpu_freq_hz / 1000000.0f);
}

float TimingDiag_GetMinUs(const TimingDiag_t* td) {
    if (td->min_cycles == 0xFFFFFFFF) return 0.0f;
    return (float)td->min_cycles / ((float)td->cpu_freq_hz / 1000000.0f);
}

float TimingDiag_GetMaxUs(const TimingDiag_t* td) {
    return (float)td->max_cycles / ((float)td->cpu_freq_hz / 1000000.0f);
}

float TimingDiag_GetAvgUs(const TimingDiag_t* td) {
    if (td->sample_count == 0) return 0.0f;
    float avg_cycles = (float)((double)td->total_cycles / (double)td->sample_count);
    return avg_cycles / ((float)td->cpu_freq_hz / 1000000.0f);
}
