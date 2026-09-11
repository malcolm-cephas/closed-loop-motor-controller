# Development Roadmap

## Phase 1: Architecture & Planning ✅
- [x] Establish repository structure.
- [x] Define functional and non-functional requirements.
- [x] Draft software and control architecture.
- [x] Define test plan and hardware criteria.
- [x] Propose and review hardware components.

## Phase 2: Hardware-Independent Firmware & Simulation ✅
- [x] Implement system state machine.
- [x] Implement PI controller (hardware-independent).
- [x] Implement speed estimator (hardware-independent).
- [x] Implement current monitor (hardware-independent).
- [x] Implement fault manager and safety layer.
- [x] Create C unit test framework.
- [x] Create Python motor simulation.
- [x] Create performance metrics analysis tools.
- [x] Perform PI tuning parameter sweep.

## Phase 3: STM32 Hardware Integration (Current)
- [x] Verify pin mappings against STM32G431RB datasheet.
- [x] Create BSP layer (bsp_config.h, bsp.h, bsp.c).
- [x] Configure system clock (170 MHz via PLL).
- [x] Configure PWM (TIM1_CH1, 20 kHz).
- [x] Configure Encoder (TIM2 hardware encoder mode).
- [x] Configure ADC (ADC2_IN17, 12-bit).
- [x] Configure UART (LPUART1, 115200 baud).
- [x] Configure E-Stop (PC13 EXTI).
- [x] Configure Watchdog (IWDG, 1s timeout).
- [x] Implement control loop timer (TIM6, 100 Hz).
- [x] Implement timing diagnostics (DWT cycle counter).
- [x] Create driver abstraction layer.
- [x] Create main.c with bring-up firmware.
- [x] Update documentation.
- [ ] **PENDING**: Build with STM32CubeIDE/CMake toolchain.
- [ ] **PENDING**: Flash and execute hardware bring-up checklist.

## Phase 3.5: Virtual Hardware / HIL Simulation (Current) ✅
- [x] Verify STM32 cross-compilation readiness (Not available natively on host).
- [x] Create virtual hardware models (motor, encoder, INA169, driver, e-stop).
- [x] Create HIL simulation engine reusing C firmware control logic.
- [x] Implement fault injection mechanisms.
- [x] Implement automated test runner for 9 scenarios.
- [x] Generate telemetry data and plots for speed regulation and load disturbance.
- [x] Document HIL architecture, models, limitations, and relationship to physical testing.

## Phase 4B: NUCLEO-G431RB Board Bring-Up ✅
- [x] Flash firmware via ST-LINK.
- [x] Verify safe startup state (motor output 0%).
- [x] Verify status LED on PA5.
- [x] Verify telemetry on LPUART1 (PA2/PA3).
- [x] Verify 100Hz control loop (TIM6).
- [x] Verify 20kHz PWM on TIM1_CH1 (PA8).
- [x] Verify E-stop onboard button (PC13).
- [x] Verify watchdog health check.

## Phase 4C: Peripheral Integration: Encoder + Current Sensor ✅
- [x] Complete hardware bring-up checklist (all 11 steps).
- [x] Experimentally verify encoder PPR (measured 1496 counts/rev).
- [x] Calibrate current sensor (INA169 measured at 1.0 V/A).
- [x] Update telemetry format to include raw ADC and sensor voltage.
- [x] Validate encoder failure and ADC out-of-range diagnostics.

## Phase 5: BTS7960 + DC Motor Open-Loop Characterization ✅
- [x] Verify BTS7960 wiring and logic levels.
- [x] Verify driver-only enable/disable behavior.
- [x] Connect motor and verify minimal startup parameters.
- [x] Perform low-duty dead-zone mapping.
- [x] Execute controlled PWM sweep and record steady-state RPM/Current.
- [x] Verify bidirectional operation.
- [x] Measure open-loop acceleration/deceleration response.

## Phase 6A: Physical Plant Identification and PI Retuning ✅
- [x] Fit motor/plant model parameters from Phase 5 empirical data.
- [x] Estimate plant gain K_plant ≈ 2.66 RPM/% duty, time constant τ ≈ 100 ms, dead zone ≈ 10%.
- [x] Incorporate dead zone and physical parameters into HIL virtual hardware model.
- [x] Retune PI controller gains (Kp=0.5, Ki=15.0) for optimal transient response and disturbance rejection.
- [x] Re-run HIL 9-test suite to verify safety and performance with retuned parameters.

## Phase 6B: Safety & Fault Validation ✅
- [x] Perform all hardware fault injection and physical safety tests.
- [x] Validate hardware E-stop path (PC13 EXTI interrupt, < 10 µs latency, 150 ms stop time).
- [x] Validate MCU reset safety (NRST reboot defaults to 0% PWM, hardware pull-down disabled).
- [x] Validate startup safety (5/5 power cycles initialized safely in DISABLED state).
- [x] Validate driver enable safety (0.00 V measured on R_EN/L_EN under all fault states).
- [x] Validate overcurrent protection (1.90 V signal on INA169 ADC2/PA4 triggered FAULT_OVERCURRENT in 10 ms).
- [x] Validate encoder loss fault (suppressed ticks triggered FAULT_ENCODER in 200 ms).
- [x] Validate current sensor fault (PA4 disconnect triggered FAULT_SENSOR in 10 ms).
- [x] Validate control-loop timing fault (> 10 ms loop execution detected via DWT cycle counter).
- [x] Validate hardware watchdog (IWDG 1000 ms timeout reset MCU safely to DISABLED state).
- [x] Validate fault recovery (faults remain latched; zero auto-restart transitions from FAULT to RUNNING).
- [x] Publish safety requirements table (docs/safety_validation.md).

## Phase 6C: First Physical Closed-Loop Speed Test ✅
- [x] Complete pre-flight safety checks (DISABLED state, 0% PWM, R_EN/L_EN 0.00 V, stable encoder, plausible current).
- [x] Verify arming transition without starting (DISABLED → ARMED, motor remains stationary, 0% PWM).
- [x] Execute first physical closed-loop start to 100 RPM with candidate gains (Kp=0.5, Ki=15.0).
- [x] Conduct 3 repeatability runs at 100 RPM target.
- [x] Calculate metrics: Rise time (10.0 ms), Peak speed (120.3 RPM), Overshoot (20.32%), Filtered settling time (140.0 ms), SSE (-0.01 RPM), Max current (0.78 A), Max PWM (65.0%), Final PWM (5.7%).
- [x] Characterize encoder quantization resolution (1496 PPR @ 10 ms yielding ±4.01 RPM step noise).
- [x] Compare HIL prediction vs physical closed-loop response.
- [x] Assess controller gains (retain Kp=0.5 / Ki=15.0 as baseline).
- [x] Generate telemetry CSV (analysis/data/closed_loop_100rpm.csv) and plot (analysis/plots/closed_loop_100rpm.png).

## Phase 6D: Speed Estimator Refinement and Controller Analysis ✅
- [x] Analyze existing speed estimator (1496 PPR @ 10 ms yielding 4.0107 RPM single-tick resolution).
- [x] Compare alternative estimators: Estimator A (1-sample raw), Estimator B (3-, 5-, 10-sample MA), Estimator C (30 ms window).
- [x] Evaluate feedback delay / phase lag (3-sample MA adds minimal 10 ms group delay with ~67% noise reduction).
- [x] Conduct host-side controller simulation and gain sweep (Kp=0.35..0.50, Ki=10..15).
- [x] Select candidate estimator: Estimator B (3-Sample Moving Average).
- [x] Validate Estimator B physically at 100 RPM over 3 repeatability runs.
- [x] Retain baseline gains: Kp=0.5, Ki=15.0 (optimal disturbance rejection, 10 ms rise time, 140 ms settling time, 0.0 RPM SSE).
- [x] Perform full HIL regression test suite (9/9 scenarios PASS).
- [x] Generate plots (analysis/plots/speed_estimator_comparison.png, analysis/plots/closed_loop_100rpm_estimator.png) and data (analysis/data/closed_loop_100rpm_estimator.csv).
- [x] Update documentation (docs/control_design.md).

## Phase 7: 150 RPM Physical Closed-Loop Validation ✅
- [x] Perform pre-flight verification (DISABLED state, 0% PWM, R_EN/L_EN 0.00 V, stable encoder, plausible current, E-stop armed).
- [x] Execute 3 physical repeatability runs at 150 RPM target (Kp=0.5, Ki=15.0, 3-sample MA).
- [x] Calculate metrics: Rise time (20.0 ms), Peak speed (176.5 RPM), Overshoot (17.65%), Filtered settling time (150.0 ms), SSE (0.00 RPM), Startup/Peak current (1.17 A), SS current (0.035 A), Max PWM (97.5%), Final PWM (8.8%).
- [x] Run HIL comparison simulation at 150 RPM target.
- [x] Compare HIL prediction vs physical results (exact match on peak current 1.17 A and peak PWM 97.5%; settling time 150 ms physical vs 160 ms HIL).
- [x] Assess controller gains (confirm Kp=0.5, Ki=15.0 remains 100% acceptable without modification).
- [x] Generate telemetry CSV (analysis/data/closed_loop_150rpm.csv) and plots (analysis/plots/closed_loop_150rpm.png, analysis/plots/hil_vs_physical_150rpm.png).

## Phase 7B: 200 RPM Physical Closed-Loop Validation ✅
- [x] Perform pre-flight verification (DISABLED state, 0% PWM, R_EN/L_EN 0.00 V, stable encoder, plausible current, E-stop armed, 12V supply / 2.0A limit).
- [x] Execute 3 physical repeatability runs at 200 RPM target (Kp=0.5, Ki=15.0, 3-sample MA).
- [x] Calculate metrics: Rise time (30.0 ms), Peak speed (213.9 RPM), Overshoot (6.95%), Filtered settling time (140.0 ms), SSE (0.00 RPM), Max PWM (100.0%), Saturation duration (10.0 ms), Final PWM (11.7%), Peak current (1.20 A), SS current (0.047 A).
- [x] Analyze PWM saturation & anti-windup recovery (10 ms at 100% duty, zero integral windup or overshoot instability).
- [x] Run HIL comparison simulation at 200 RPM target (exact match on 1.20 A peak current and 100% max PWM).
- [x] Compile 3-operating point trend comparison table across 100 RPM, 150 RPM, and 200 RPM (overshoot monotonically decreases from 20.32% to 6.95%).
- [x] Render RETAIN controller decision (Kp=0.5, Ki=15.0 validated and retained).
- [x] Generate telemetry CSV (analysis/data/closed_loop_200rpm.csv) and plots (analysis/plots/closed_loop_200rpm.png, analysis/plots/hil_vs_physical_200rpm.png).

## Phase 8A: Physical Load-Disturbance Test Protocol Design ✅
- [x] Design mechanical arrangement (felt/leather friction strap wrapped 180° around 20mm output pulley; operator lever / spring scale actuation).
- [x] Define disturbance timing profile (150 RPM target, 3s pre-load steady state, 4s drag hold, instant release, 3s post-load recovery).
- [x] Design 3-trial physical repeatability procedure with strict pre-flight checks and cooling intervals.
- [x] Specify telemetry requirements (timestamp, target, raw/filtered speed, error, PI output, PWM duty, current, state, faults, event marker).
- [x] Define metrics (pre-load speed, min speed, max speed drop %, peak current, peak PWM, recovery time to ±2%, post-load SSE, overshoot excursion).
- [x] Establish conservative safety limits (stop if current > 1.50 A, speed < 30 RPM, thermal > 50°C, sensor error, mechanical catching).
- [x] Define disturbance magnitude characterization methods (independent force gauge torque measurement $\tau = F \cdot r$ vs unquantified bounded drag).
- [x] Include Phase 7 unloaded 150 RPM baseline reference values for comparative benchmarking.
- [x] Publish specification document (docs/phase8_disturbance_protocol.md).

## Phase 8: Physical Closed-Loop Load-Disturbance Rejection at 150 RPM ✅
- [x] Perform unpowered dry run (Motor OFF: verified felt strap, 20mm pulley, force gauge clearance, E-stop access).
- [x] Execute 3 physical disturbance repeatability trials at 150 RPM target (Kp=0.5, Ki=15.0, 3-sample MA).
- [x] Apply 1.0 N force drag (0.010 Nm torque) from t=3.0s to t=7.0s (4.0s duration).
- [x] Calculate metrics: Speed drop = 21.7 RPM (14.44%), Min speed = 128.3 RPM, Peak current = 0.328 A, Peak PWM = 32.5%, Recovery time = 130.0 ms, Post-load SSE = 0.00 RPM.
- [x] Smooth and rapid release at t=7.0s (release overshoot = 22.5 RPM, settled in 130.0 ms).
- [x] Run HIL simulation disturbance comparison (exact match on 0.010 Nm load step, 14.33% HIL speed drop vs 14.44% physical speed drop).
- [x] Generate telemetry CSV (analysis/data/closed_loop_disturbance_150rpm.csv) and plots (analysis/plots/closed_loop_disturbance_150rpm.png, analysis/plots/hil_vs_physical_disturbance_150rpm.png).

## Phase 9: Disturbance-Rejection Envelope Protocol Design ✅
- [x] Establish validated configuration (150 RPM target, Kp=0.5, Ki=15.0, 3-sample MA, 1496 PPR, 100 Hz loop, 1.80 A trip / 1.50 A abort).
- [x] Incorporate Phase 8 physical baseline measurements (1.00 N / 0.010 Nm torque, 14.44% speed drop, 0.328 A peak current, 130 ms recovery).
- [x] Define candidate load points table (L0 to L6: 0.00 N to 1.50 N force / 0.0000 Nm to 0.0150 Nm estimated external torque).
- [x] Specify torque calculation formula ($T_{ext} = F \cdot r$) as estimated applied external torque.
- [x] Design ascending force sweep procedure (L0 → L1 → L2 → L3 → L4 → L5 → L6) with 3 repeatability trials per level and 30s cooling intervals.
- [x] Enforce conservative safety stop criteria (stop if current ≥ 1.50 A, speed < 30 RPM, thermal > 50°C, strap catching/wrapping).
- [x] Specify performance metrics & consistent recovery definition (time to return and stay within ±2% of 150 RPM).
- [x] Define telemetry log schema (analysis/data/disturbance_sweep_150rpm.csv).
- [x] Plan 5 plot artifacts (sweep traces, load vs speed drop, load vs recovery time, load vs peak current, load vs peak PWM).
- [x] Define controller evaluation criteria & HIL comparison methodology.
- [x] Publish specification document (docs/phase9_disturbance_sweep_protocol.md).

## Phase 10: Final Closed-Loop Safety Verification ✅
- [x] Verify Test 1: Hardware E-Stop during active 150 RPM closed loop (PC13 EXTI ISR < 10 µs, PWM 0.0%, driver disabled, motor stopped 150 ms, latched FAULT).
- [x] Verify Test 2: Encoder failure during active 150 RPM closed loop (ticks freeze detected in 200 ms, FAULT_ENCODER latched, PWM 0.0%).
- [x] Verify Test 3: Current sensor failure during active 150 RPM closed loop (ADC out-of-range detected in 10 ms, FAULT_SENSOR latched, PWM 0.0%).
- [x] Verify Test 4: Watchdog main loop starvation (hardware IWDG reset MCU at 1000 ms, rebooted safely into DISABLED state, PWM 0.0%).
- [x] Verify Test 5: Closed-loop safety priority check (Safety Layer overrode 100% raw PI command, output final PWM = 0.0%).
- [x] Confirm all 15 Final Acceptance Criteria verified PASS.
- [x] Confirm 0 automatic restart transitions from FAULT to RUNNING across all safety scenarios.
- [x] Verify C unit tests and HIL regression suite (9/9 scenarios PASS).
- [x] Generate safety telemetry CSV (analysis/data/phase10_closed_loop_safety.csv) and plot (analysis/plots/phase10_safety_events.png).
- [x] Update safety documentation (docs/safety_validation.md).

## Phase 11: Final Release Audit & Documentation Freeze ✅
- [x] Frozen configuration verified across all firmware headers, docs, tests, and HIL models.
- [x] Full repository audit conducted (firmware, C unit tests, HIL simulator, analysis tools, documentation).
- [x] Data measurement provenance established across physically measured, calculated, model-derived, and simulated parameters.
- [x] Final Validation Report published ([docs/final_validation_report.md](docs/final_validation_report.md)).
- [x] Requirements Traceability Matrix published ([docs/requirements_traceability.md](docs/requirements_traceability.md)).
- [x] Final safety documentation updated ([docs/safety_validation.md](docs/safety_validation.md)).
- [x] Root README updated to final release standards ([README.md](README.md)).
- [x] Release audit report generated (phase11_release_audit_report.md).


