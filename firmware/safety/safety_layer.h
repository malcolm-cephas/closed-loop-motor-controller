#ifndef SAFETY_LAYER_H
#define SAFETY_LAYER_H

#include <stdbool.h>

typedef struct {
    float max_motor_command;
    float max_slew_rate; // Units per second
} SafetyConfig_t;

void SafetyLayer_Init(SafetyConfig_t config);
float SafetyLayer_ProcessCommand(float requested_command, float dt);

#endif
