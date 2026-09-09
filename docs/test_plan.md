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
