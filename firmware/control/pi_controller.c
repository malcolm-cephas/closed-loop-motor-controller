#include "pi_controller.h"

void PI_Init(PI_Controller_t* pi, PI_Config_t config) {
    pi->config = config;
    pi->integral_sum = 0.0f;
}

void PI_Reset(PI_Controller_t* pi) {
    pi->integral_sum = 0.0f;
}

float PI_Calculate(PI_Controller_t* pi, float target, float measured, float dt) {
    if (dt <= 0.0f) return 0.0f;

    float error = target - measured;
    float proportional = pi->config.kp * error;
    
    float temp_integral = pi->integral_sum + (pi->config.ki * error * dt);
    float output = proportional + temp_integral;

    bool saturate_high = (output > pi->config.out_max);
    bool saturate_low = (output < pi->config.out_min);

    if ((saturate_high && error > 0.0f) || (saturate_low && error < 0.0f)) {
        // Anti-windup: Do not accumulate integral
    } else {
        pi->integral_sum = temp_integral;
    }

    if (output > pi->config.out_max) {
        output = pi->config.out_max;
    } else if (output < pi->config.out_min) {
        output = pi->config.out_min;
    }

    return output;
}
