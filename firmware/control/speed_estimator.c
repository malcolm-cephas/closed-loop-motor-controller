#include "speed_estimator.h"

void SpeedEstimator_Init(SpeedEstimator_t* estimator, SpeedEstimatorConfig_t config) {
    estimator->config = config;
    estimator->previous_counts = 0;
}

float SpeedEstimator_CalculateRPM_CountBased(SpeedEstimator_t* estimator, int32_t current_counts, float dt) {
    if (dt <= 0.0f || estimator->config.counts_per_output_revolution <= 0.0f) {
        return 0.0f;
    }

    int32_t delta_counts = current_counts - estimator->previous_counts;
    estimator->previous_counts = current_counts;

    float revs_per_second = (float)delta_counts / (estimator->config.counts_per_output_revolution * dt);
    return revs_per_second * 60.0f;
}
