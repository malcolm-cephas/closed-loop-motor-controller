#include <stdio.h>
#include <assert.h>
#include <math.h>

#include "../firmware/app/system_state.h"
#include "../firmware/safety/fault_manager.h"
#include "../firmware/safety/safety_layer.h"
#include "../firmware/control/pi_controller.h"
#include "../firmware/control/speed_estimator.h"

#define ASSERT_FLOAT_EQ(expected, actual, epsilon) assert(fabs((expected) - (actual)) < (epsilon))

void test_pi_controller() {
    PI_Controller_t pi;
    PI_Config_t cfg = { .kp = 1.0f, .ki = 0.5f, .out_max = 100.0f, .out_min = -100.0f };
    PI_Init(&pi, cfg);

    // Test zero error
    float out = PI_Calculate(&pi, 100.0f, 100.0f, 0.01f);
    ASSERT_FLOAT_EQ(0.0f, out, 0.001f);

    // Test positive error (P term)
    out = PI_Calculate(&pi, 100.0f, 90.0f, 0.01f); // err=10, P=10, I=0.5*10*0.01=0.05
    ASSERT_FLOAT_EQ(10.05f, out, 0.001f);

    // Test negative error
    out = PI_Calculate(&pi, 90.0f, 100.0f, 0.01f); // err=-10, P=-10, I=(prev 0.05) - 0.05 = 0
    ASSERT_FLOAT_EQ(-10.0f, out, 0.001f);

    // Test Saturation and Windup
    PI_Reset(&pi);
    out = PI_Calculate(&pi, 1000.0f, 0.0f, 0.01f); // Huge error, P=1000 -> saturated to 100
    ASSERT_FLOAT_EQ(100.0f, out, 0.001f);
    // Because it's saturated, integral sum should not accumulate positively
    float integral_before = pi.integral_sum;
    out = PI_Calculate(&pi, 1000.0f, 0.0f, 0.01f);
    assert(pi.integral_sum == integral_before); // windup protected
    
    printf("PI Controller tests passed.\n");
}

void test_speed_estimator() {
    SpeedEstimator_t est;
    SpeedEstimatorConfig_t cfg = { .counts_per_output_revolution = 1000.0f };
    SpeedEstimator_Init(&est, cfg);

    // dt = 0.01s. Delta counts = 10.
    // 10 counts in 0.01s = 1000 counts/sec = 1 rev/sec = 60 RPM
    float rpm = SpeedEstimator_CalculateRPM_CountBased(&est, 10, 0.01f);
    ASSERT_FLOAT_EQ(60.0f, rpm, 0.001f);

    // Reverse direction
    rpm = SpeedEstimator_CalculateRPM_CountBased(&est, 0, 0.01f); // goes from 10 to 0, delta = -10
    ASSERT_FLOAT_EQ(-60.0f, rpm, 0.001f);

    // Zero speed
    rpm = SpeedEstimator_CalculateRPM_CountBased(&est, 0, 0.01f);
    ASSERT_FLOAT_EQ(0.0f, rpm, 0.001f);

    printf("Speed Estimator tests passed.\n");
}

void test_state_machine_and_safety() {
    SystemState_Init();
    FaultManager_Init();
    SafetyConfig_t s_cfg = { .max_motor_command = 100.0f, .max_slew_rate = 50.0f };
    SafetyLayer_Init(s_cfg);

    // Initial state is INIT -> DISABLED (manually requested)
    SystemState_RequestDisabled();
    assert(SystemState_Get() == SYSTEM_STATE_DISABLED);

    // Safety layer should force output to 0 if not RUNNING
    float safe_out = SafetyLayer_ProcessCommand(50.0f, 0.01f);
    assert(safe_out == 0.0f);

    // Try to arm without safety met
    bool armed = SystemState_RequestArmed(false, true, true, true, 0.0f);
    assert(armed == false);

    // Arm properly
    armed = SystemState_RequestArmed(true, true, true, true, 0.0f);
    assert(armed == true);
    assert(SystemState_Get() == SYSTEM_STATE_ARMED);

    // Start running
    bool running = SystemState_RequestRunning();
    assert(running == true);
    assert(SystemState_Get() == SYSTEM_STATE_RUNNING);

    // Process valid command (slew rate 50/sec * 0.01s = 0.5 max delta)
    safe_out = SafetyLayer_ProcessCommand(50.0f, 0.01f);
    // previous was 0, max delta is 0.5
    ASSERT_FLOAT_EQ(0.5f, safe_out, 0.001f);

    // Trigger Fault
    FaultManager_SetFault(FAULT_ESTOP);
    assert(SystemState_Get() == SYSTEM_STATE_FAULT);
    
    // Safety layer should force 0
    safe_out = SafetyLayer_ProcessCommand(50.0f, 0.01f);
    assert(safe_out == 0.0f);

    printf("State Machine & Safety Layer tests passed.\n");
}

int main() {
    test_pi_controller();
    test_speed_estimator();
    test_state_machine_and_safety();
    printf("All C Unit Tests Passed Successfully!\n");
    return 0;
}
