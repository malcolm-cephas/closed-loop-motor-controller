#include "safety_layer.h"
#include "../app/system_state.h"
#include "fault_manager.h"

static SafetyConfig_t _config;
static float previous_command = 0.0f;

void SafetyLayer_Init(SafetyConfig_t config) {
    _config = config;
    previous_command = 0.0f;
}

static float clamp(float value, float max_val, float min_val) {
    if (value > max_val) return max_val;
    if (value < min_val) return min_val;
    return value;
}

float SafetyLayer_ProcessCommand(float requested_command, float dt) {
    SystemState_t state = SystemState_Get();
    bool fault_active = FaultManager_HasActiveFault();

    if (state != SYSTEM_STATE_RUNNING || fault_active) {
        previous_command = 0.0f;
        return 0.0f;
    }

    if (_config.max_slew_rate > 0.0f && dt > 0.0f) {
        float max_delta = _config.max_slew_rate * dt;
        float delta = requested_command - previous_command;
        delta = clamp(delta, max_delta, -max_delta);
        requested_command = previous_command + delta;
    }

    requested_command = clamp(requested_command, _config.max_motor_command, -_config.max_motor_command);
    
    previous_command = requested_command;
    return requested_command;
}
