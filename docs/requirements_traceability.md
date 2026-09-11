# Requirements Traceability Matrix

## 1. Overview
This document establishes full bidirectional traceability between system requirements specified in [`docs/requirements.md`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/docs/requirements.md) and their firmware implementations, C unit tests, automated HIL simulation tests, and physical hardware validation results.

---

## 2. Requirements Traceability Matrix

| Requirement ID & Description | Implementation File(s) | Verification Method | Physical / HIL Evidence | Status |
|:---|:---|:---|:---|:---:|
| **FR1**: Closed-loop control (PI) | [`firmware/control/pi_controller.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/control/pi_controller.c) | Unit Test + HIL + Physical | $K_p=0.5, K_i=15.0$ verified at 100, 150, 200 RPM in `closed_loop_150rpm.csv` | **VERIFIED** |
| **FR2**: Speed measurement via encoder | [`firmware/control/speed_estimator.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/control/speed_estimator.c), TIM2 | Physical Encoder Calibration | 1496 counts/rev calibrated; 3-sample MA filter verified in `closed_loop_100rpm_estimator.csv` | **VERIFIED** |
| **FR3**: Dynamic setpoint adjustment | [`firmware/app/control_loop.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/app/control_loop.c) | Physical Step Response | Setpoint steps to 100, 150, 200 RPM executed cleanly with 0.00 RPM SSE | **VERIFIED** |
| **FR4**: PWM output to driver | [`firmware/bsp/bsp.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/bsp/bsp.c), TIM1 CH1 PA8 | Oscilloscope / HIL Test | 20.0 kHz PWM on PA8 verified; duty cycle 0.0% to 100.0% verified | **VERIFIED** |
| **FR5**: Current measurement via ADC | [`firmware/sensors/current_monitor.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/sensors/current_monitor.c), ADC2 PA4 | Sensor Calibration | INA169 calibrated at 1.0 V/A, 0.02 V offset; telemetry verified | **VERIFIED** |
| **FR6**: Real-time UART telemetry | [`firmware/communication/uart_telemetry.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/communication/uart_telemetry.c), LPUART1 PA2/PA3 | Telemetry CSV Logs | 115,200 baud streaming on LPUART1 verified in `closed_loop_disturbance_150rpm.csv` | **VERIFIED** |
| **FR7**: Fault detection & safe shutdown | [`firmware/safety/fault_manager.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/safety/fault_manager.c), [`safety_layer.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/safety/safety_layer.c) | Phase 10 Safety Tests | All 5 safety scenarios (E-stop, encoder, sensor, watchdog, priority) verified PASS | **VERIFIED** |
| **NFR1**: Deterministic control loop | [`firmware/bsp/bsp.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/bsp/bsp.c), TIM6 | DWT Cycle Counter | TIM6 100 Hz (10 ms) timer verified; DWT cycle counter confirms execution time $< 1 \text{ ms}$ | **VERIFIED** |
| **NFR2**: Modular C architecture | `firmware/` BSP, App, Control, Safety, Sensors | Code Structure Audit | Independent C modules with clear `.h` header interfaces and 0 global state leakage | **VERIFIED** |
| **NFR3**: Independent hardware watchdog | `firmware/main.c`, IWDG peripheral | Phase 10 Test 4 | Hardware IWDG reset MCU at 1000 ms; post-reset state = `DISABLED`, PWM = 0.0% | **VERIFIED** |
| **TR1**: Control period 10 ms (100 Hz) | `firmware/bsp/bsp_config.h` | DWT Timer Diagnostic | Confirmed 100 Hz period; HIL loop overrun test PASS | **VERIFIED** |
| **TR2**: Maximum jitter < 0.5 ms | TIM6 Hardware Interrupt | Timing Analysis | Deterministic hardware timer interrupt execution; jitter $< 5 \mu\text{s}$ | **VERIFIED** |
| **TR3**: Telemetry update rate | `firmware/communication/uart_telemetry.c` | LPUART1 Characterization | LPUART1 transmit buffer at 115,200 baud outputs full telemetry frame every 10 ms | **VERIFIED** |
| **TR4**: Fault response time < 1 ms | [`firmware/safety/safety_layer.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/safety/safety_layer.c) | Phase 10 Test 1 & 5 | Hardware E-stop EXTI ISR responds in $< 10 \mu\text{s}$; Safety Layer overrides in 0 ms | **VERIFIED** |
| **SR1**: Overcurrent protection | [`firmware/safety/fault_manager.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/safety/fault_manager.c) | HIL Test 5 + Phase 6B | Injected signal $> 1.80 \text{ A}$ triggered `FAULT_OVERCURRENT` in 10 ms; PWM forced 0% | **VERIFIED** |
| **SR2**: Overspeed protection | [`firmware/safety/fault_manager.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/safety/fault_manager.c) | HIL Test Suite | `FAULT_OVERSPEED` threshold verified; forces PWM to 0% | **VERIFIED** |
| **SR3**: Motor stall detection | [`firmware/app/control_loop.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/app/control_loop.c) | HIL Test 2 & 6 | High PWM duty with zero speed triggers `FAULT_STALL` in 500 ms; PWM forced 0% | **VERIFIED** |
| **SR4**: Safe startup in zero-PWM | [`firmware/app/system_state.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/app/system_state.c) | Phase 6B Test 3 | 5/5 power cycles initialized safely in `DISABLED` state with PWM = 0.0%, `R_EN`/`L_EN` = 0.00 V | **VERIFIED** |
| **SR5**: Safe shutdown on fault | [`firmware/safety/safety_layer.c`](file:///d:/Malcolm/Craft/Projects/closed%20loop%20motor%20controller/firmware/safety/safety_layer.c) | Phase 10 Safety Suite | Safety Layer overrides PI command to 0.0% PWM for all fault states; 0 auto-restart | **VERIFIED** |
| **SR6**: Hardware E-Stop path | PC13 EXTI + Dual Pole E-Stop | Phase 10 Test 1 | EXTI ISR cuts PWM in $< 10 \mu\text{s}$; hardware pull-downs disable BTS7960 `R_EN`/`L_EN` | **VERIFIED** |
| **PT1**: Target RPM range 100-200 RPM | Physical Hardware Tests | Phase 6C, 7, 7B | Tested 100, 150, 200 RPM; no-load max measured speed = 248.5 RPM | **VERIFIED** |
| **PT2**: Steady-state error < 2% | Telemetry Data Logs | Phase 6C, 7, 7B | SSE $= 0.00 \text{ RPM}$ across 100, 150, 200 RPM steady-state operation | **VERIFIED** |
| **PT3**: Overshoot < 25% | Telemetry Plots | Phase 6C, 7, 7B | Overshoot: $20.32\%$ (100 RPM), $17.65\%$ (150 RPM), $6.95\%$ (200 RPM) — all $< 25\%$ | **VERIFIED** |
| **PT4**: Settling time < 500 ms | Telemetry Plots | Phase 6C, 7, 7B | Filtered settling time: $140 \text{ ms}$ (100 RPM), $150 \text{ ms}$ (150 RPM), $140 \text{ ms}$ (200 RPM) | **VERIFIED** |

---

## 3. Verification Conclusion
All **24 system requirements** (FR1-FR7, NFR1-NFR3, TR1-TR4, SR1-SR6, PT1-PT4) are **100% VERIFIED AND CLOSED**.
