#ifndef SPEED_ESTIMATOR_H
#define SPEED_ESTIMATOR_H

#include <stdint.h>

typedef struct {
    float counts_per_output_revolution; // e.g., Motor PPR * Gearbox Ratio * Decoding Factor
} SpeedEstimatorConfig_t;

typedef struct {
    SpeedEstimatorConfig_t config;
    int32_t previous_counts;
} SpeedEstimator_t;

void SpeedEstimator_Init(SpeedEstimator_t* estimator, SpeedEstimatorConfig_t config);
float SpeedEstimator_CalculateRPM_CountBased(SpeedEstimator_t* estimator, int32_t current_counts, float dt);

#endif
