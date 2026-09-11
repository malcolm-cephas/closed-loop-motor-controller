# Test Plan

## 1. PC Unit Tests (C Framework)
Hardware-independent C code is tested natively on the host PC (`tests/unit_tests.c`).
- **PI Controller**: Zero error, positive error, negative error, output saturation, anti-windup clamping, state resets.
- **Speed Estimator**: Correct scaling given a fixed delta count and delta t, negative speed, and zero speed.
- **State Machine**: Verification of invalid state transitions (e.g., cannot go to `ARMED` with faults), proper E-stop fault latching.
- **Safety Layer**: Verification that max slew rate and absolute saturation limits override PI requested commands.

## 2. Python Simulation
The `motor_sim.py` models the physical DC motor in discrete time, executing the exact conceptual PI logic used in C.
- Models step response, load disturbance, measurement noise (encoder quantization).
- Outputs CSV telemetry to be processed by `performance_metrics.py`.

## 3. Hardware Bring-Up Procedure (Phase 3)

This procedure must be followed sequentially. Do NOT skip steps.

| Step | Test | Input | Expected Result | Pass Criteria | Status |
|:---|:---|:---|:---|:---|:---|
| 1 | Build firmware | Compile project | No errors | Exit code 0 | **PASS** |
| 2 | Flash NUCLEO | ST-LINK | Board boots | No hard fault | **PASS** |
| 3 | Startup verification | Power on | System enters DISABLED state | UART banner appears | **PASS** |
| 4 | Status LED | Observe PA5 | LED toggles at ~1 Hz | Visible blinking | **PASS** |
| 5 | UART telemetry | PC terminal 115200 | CSV lines appear | Valid format, ~100 Hz | **PASS** |
| 6 | Control timer | Oscilloscope/logic analyzer | TIM6 ISR fires at 100 Hz | 10 ms ± 0.5 ms | **PASS** (100.2Hz) |
| 7 | PWM output | Oscilloscope on PA8 | 20 kHz, 0% duty (disabled) | Correct frequency | **PASS** (20.01kHz)|
| 8 | Encoder input | Manual rotation on PA0/PA1 | Counter increments cleanly | Count matches expected | **PASS** (1496 PPR) |
| 9 | ADC input | Known voltage/current on PA4 | ADC reading matches load | Within ±5% | **PASS** (1.0 V/A) |
| 10 | E-stop input | Press B1 (PC13) | FAULT_ESTOP set, telemetry shows fault | State = FAULT | **PASS** |
| 11 | Watchdog | Inject infinite loop | MCU resets within ~1s | Board restarts | **PASS** (1.05s) |

> [!CAUTION]
> PWM output must remain disconnected from the motor driver during all bring-up steps.
> Only after ALL steps pass should the motor driver be physically wired.

## 4. Hardware/System Tests (Phase 4, after motor connection)
- **PWM Output**: Command 25%, 50%, 75% duty cycles. Verify with oscilloscope.
- **Encoder Measurement**: Spin motor open-loop. Count pulses and calculate actual PPR.
- **Current Measurement**: Apply known resistive load. Compare ADC reading to multimeter.

## 5. Control Tests (Phase 4)
- **Step Response**: Step from 0 to target RPM. Measure rise time, overshoot, settling.
- **Load Disturbance**: Apply friction during steady state. Measure recovery.
- **Multiple RPM Values**: Verify at 100, 500, 1000, 2000 RPM.

## 6. Fault Tests (Phase 5)
- **Encoder disconnected**: Unplug encoder while running. Expect stall/sensor fault.
- **Motor stalled**: Lock rotor. Expect overcurrent or stall protection.
- **Watchdog timeout**: Inject software hang. Expect MCU reset.
