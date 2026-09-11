# HIL (Hardware-in-the-Loop) Testing Documentation

## Overview

The HIL test environment allows the hardware-independent control firmware to be
exercised against simulated hardware without requiring the physical NUCLEO-G431RB,
motor, encoder, BTS7960, or INA169.

> [!WARNING]
> **HIL testing does NOT replace physical hardware validation.**
> All simulation parameters are unverified assumptions. Real hardware testing
> with calibrated instruments is mandatory before operating the motor.

## Architecture

```text
┌──────────────────────────────────────────────────┐
│           HIL Test Runner (Python)                │
│           run_hil_tests.py                        │
├──────────────────────────────────────────────────┤
│           HIL Engine (hil_engine.py)              │
│  ┌─────────────────┐ ┌────────────────────────┐  │
│  │ PI Controller    │ │ State Machine          │  │
│  │ Speed Estimator  │ │ Fault Manager          │  │
│  │ Current Monitor  │ │ Safety Layer           │  │
│  │ (same equations  │ │ (same logic as C code) │  │
│  │  as C firmware)  │ │                        │  │
│  └─────────────────┘ └────────────────────────┘  │
│           ↕ (virtual BSP interface)               │
├──────────────────────────────────────────────────┤
│    Virtual Hardware (virtual_hardware.py)          │
│  ┌───────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ DC Motor   │ │ Encoder  │ │ Current Sensor │  │
│  │ Model      │ │ Model    │ │ Model          │  │
│  └───────────┘ └──────────┘ └────────────────┘  │
│  ┌───────────┐ ┌──────────┐                      │
│  │ BTS7960    │ │ E-Stop   │                      │
│  │ Driver     │ │ Button   │                      │
│  └───────────┘ └──────────┘                      │
└──────────────────────────────────────────────────┘
```

## Virtual Hardware Models

### DC Motor Model

| Parameter | Identified Value | Unit | Status |
|:---|:---|:---|:---|
| Armature Resistance (R) | 10.0 | Ω | IDENTIFIED (Phase 6A) |
| Back-EMF Constant (Ke) | 0.045 | V/(rad/s) | IDENTIFIED (Phase 6A) |
| Torque Constant (Kt) | 0.045 | Nm/A | IDENTIFIED (Phase 6A) |
| Rotor Inertia (J) | 0.00005 | kg·m² | ESTIMATED (Phase 6A) |
| Viscous Friction (B) | 0.0001 | Nm/(rad/s) | IDENTIFIED (Phase 6A) |
| Stiction Torque (T_stiction) | 0.005 | Nm | IDENTIFIED (Phase 6A: 10% dead zone) |
| Supply Voltage | 12.0 | V | MEASURED (Phase 5) |
| Max No-Load RPM | 248.5 | RPM | MEASURED (Phase 5) |

**Equations:**
- Electrical: `I = (V_applied - Ke * ω) / R`
- Mechanical: `J * dω/dt = Kt * I - B * ω - T_stiction * sign(ω) - T_load`

### Quadrature Encoder Model
- Generates cumulative integer counts from continuous angular position
- Supports forward/reverse rotation and zero speed
- Configuration: **1496 counts/rev** (Verified physically via 10 manual shaft revolutions)
- Configurable via `counts_per_output_rev` parameter

### Current Sensor Model (INA169)
- Converts motor current → sensor voltage → ADC counts
- Configuration sensitivity: **1.0 V/A** (Verified physically via known resistive loads)
- Zero-current offset: **0.02V / ~24 counts** (Verified physically)
- Optional noise, offset, gain error
- ADC: 12-bit, 3.3V reference

### BTS7960 Driver Model
- Models enable state and fault condition
- Effective duty = 0% when disabled or faulted
- Safety layer retains final authority

### E-Stop Model
- Simple press/release interface
- Triggers FAULT_ESTOP when pressed

## Fault Injection Capabilities

| Fault Type | Injection Method | Expected Response |
|:---|:---|:---|
| E-Stop | `engine.estop.press()` | FAULT_ESTOP, output → 0, state → FAULT |
| Overcurrent | High target RPM or low motor resistance | FAULT_OVERCURRENT, output → 0 |
| Encoder Failure | Freeze encoder count while motor runs | FAULT_ENCODER, output → 0 |
| Driver Fault | `engine.driver.set_fault(True)` | FAULT_DRIVER, output → 0 |
| Loop Overrun | `engine.inject_overrun = True` | `loop_time_us > 10000` detected |
| Watchdog Failure | Skip `tick_main_loop()` calls | `watchdog_triggered = True` |

## Test Scenarios

| # | Test | Assertions | Status |
|:---|:---|:---|:---|
| 1 | Startup | INIT→DISABLED→ARMED, output=0 throughout | PASS |
| 2 | 200 RPM Regulation | Speed within 2% of target after 5s | PASS |
| 3 | Load Disturbance | Speed recovers to within 2% after 0.01 Nm step | PASS |
| 4 | E-Stop During Running | Immediate output→0, state→FAULT, cannot re-enable | PASS |
| 5 | Overcurrent | Fault detected, motor disabled | PASS |
| 6 | Encoder Failure | Fault detected when encoder frozen while motor runs | PASS |
| 7 | Driver Fault | FAULT_DRIVER set, output→0 | PASS |
| 8 | Loop Overrun | Simulated execution time > 10ms detected | PASS |
| 9 | Watchdog Health | Starvation of main loop causes watchdog timeout | PASS |

## Generated Outputs

| File | Description |
|:---|:---|
| `analysis/data/hil_speed_regulation.csv` | Full telemetry from 200 RPM regulation test |
| `analysis/data/hil_load_disturbance.csv` | Full telemetry from load disturbance test |
| `analysis/plots/hil_speed_regulation.png` | RPM, PWM, current vs time |
| `analysis/plots/hil_load_disturbance.png` | RPM, PWM, current vs time with load step |

## Limitations

1. **Motor parameters are assumptions.** The model does NOT represent the actual JGA25-370.
2. **No electrical dynamics.** Armature inductance is neglected (steady-state electrical model).
3. **Simplified friction.** Viscous damping and static friction/stiction threshold are modeled, but velocity-dependent dynamic Stribeck friction curve is simplified.
4. **No gear backlash.** The gearbox is modeled as a perfect ratio.
5. **No PWM ripple.** The motor sees averaged voltage, not individual PWM pulses.
6. **No sampling delay.** ADC conversion and computation latency are not modeled.
7. **No thermal effects.** Motor resistance and current limits are fixed.
8. **Deterministic noise.** ADC noise uses a simple PRNG, not a realistic noise model.

## Relationship to Physical Testing

```text
HIL Testing                    Physical Testing
──────────                     ────────────────
Validates control logic        Validates real hardware
Uses assumed parameters        Uses measured parameters
Runs on PC                     Runs on STM32G431RB
No real motor                  Real motor + encoder
No real current                Real current sensor
No real PWM                    Real PWM on oscilloscope
Catches software bugs          Catches hardware bugs
Does NOT prove safety          Required to prove safety
```

HIL is a **software confidence tool**. Physical bring-up and testing remain mandatory.
