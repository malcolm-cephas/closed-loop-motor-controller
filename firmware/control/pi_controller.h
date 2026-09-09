#ifndef PI_CONTROLLER_H
#define PI_CONTROLLER_H

#include <stdbool.h>

typedef struct {
    float kp;
    float ki;
    float out_max;
    float out_min;
} PI_Config_t;

typedef struct {
    PI_Config_t config;
    float integral_sum;
} PI_Controller_t;

void PI_Init(PI_Controller_t* pi, PI_Config_t config);
void PI_Reset(PI_Controller_t* pi);
float PI_Calculate(PI_Controller_t* pi, float target, float measured, float dt);

#endif
