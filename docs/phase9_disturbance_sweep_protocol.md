# Phase 9 — Disturbance-Rejection Envelope Protocol Specification

## Executive Overview
This document specifies the safety, mechanical, procedural, telemetry, and analytical protocols for executing a controlled physical **disturbance-rejection envelope sweep** on the closed-loop DC motor controller operating at **150 RPM**. 

The goal of this sweep is to systematically map how closed-loop speed regulation, control effort ($\Delta \text{PWM}$), electrical current ($\Delta I$), and speed recovery time ($t_{rec}$) evolve as applied mechanical load torque increases from $0.00 \text{ N}$ up to a candidate maximum of $1.50 \text{ N}$ force ($0.0150 \text{ N}\cdot\text{m}$ estimated external torque).

---

## 1. Validated Hardware & Control Configuration

This protocol enforces the exact validated hardware and firmware configuration:

- **Microcontroller**: STM32G431RBT6 / NUCLEO-G431RB
- **DC Motor**: JGA25-370 12 V DC gear motor with 1496 PPR Hall quadrature encoder
- **Motor Driver**: BTS7960 43 A H-bridge module
- **Current Sensor**: INA169 calibrated at $1.0 \text{ V/A}$ sensitivity, $0.02 \text{ V}$ zero-current offset
- **Power Supply**: $12.0 \text{ V}$ DC supply with bench current limit set to $2.0 \text{ A}$
- **Firmware Over-Current Trip Threshold**: $1.80 \text{ A}$
- **Experimental Safety Abort Limit**: $1.50 \text{ A}$
- **Control Loop Rate**: $100 \text{ Hz}$ ($10 \text{ ms}$ sampling period $dt$)
- **PWM Frequency**: $20 \text{ kHz}$
- **PI Controller Gains**: $K_p = 0.5$, $K_i = 15.0$ (Hardware-independent discrete PI with anti-windup)
- **Speed Estimator**: 3-sample moving average filter
- **Primary Safety**: Physical PC13 E-stop button (hardware EXTI interrupt)

---

## 2. Validated Baseline Reference (Phase 8 Physical Results)

Phase 8 established the single-point physical load disturbance reference at $1.00 \text{ N}$ force:

| Parameter / Metric | Phase 8 Physical Reference Value |
|:---|:---:|
| **Target Speed** | $150.0 \text{ RPM}$ |
| **Applied Force ($F$)** | $1.00 \text{ N}$ |
| **Pulley Radius ($r$)** | $10 \text{ mm} = 0.010 \text{ m}$ |
| **Estimated External Torque ($T_{ext}$)** | $0.0100 \text{ N}\cdot\text{m}$ |
| **Pre-Load Mean Speed** | $150.01 \text{ RPM}$ |
| **Minimum Speed Under Disturbance** | $128.34 \text{ RPM}$ |
| **Maximum Speed Drop ($\Delta N_{drop}$)** | $21.66 \text{ RPM}$ |
| **Percentage Speed Drop ($\% \Delta N$)** | **$14.44\%$** |
| **Peak Current Under Disturbance** | **$0.328 \text{ A}$** |
| **Peak PWM Duty Under Disturbance** | **$32.49\%$** |
| **Speed Recovery Time ($t_{rec}$)** | **$130.0 \text{ ms}$** |
| **Post-Load Steady-State Error** | $0.00 \text{ RPM}$ |
| **Active Fault Flags** | `FAULT_NONE` ($0x00$) |

---

## 3. Candidate Load Points & Disturbance Envelope

The disturbance-rejection envelope sweep evaluates candidate force levels applied using the $20 \text{ mm}$ diameter smooth aluminum pulley ($r = 0.010 \text{ m}$) and felt/leather friction strap:

| Load Level ID | Candidate Applied Force ($F$) | Estimated External Torque ($T_{ext} = F \cdot r$) | Status / Role |
|:---:|:---:|:---:|:---|
| **L0** | $0.00 \text{ N}$ | $0.0000 \text{ N}\cdot\text{m}$ | Unloaded Baseline |
| **L1** | $0.25 \text{ N}$ | $0.0025 \text{ N}\cdot\text{m}$ | Candidate Test Point |
| **L2** | $0.50 \text{ N}$ | $0.0050 \text{ N}\cdot\text{m}$ | Candidate Test Point |
| **L3** | $0.75 \text{ N}$ | $0.0075 \text{ N}\cdot\text{m}$ | Candidate Test Point |
| **L4** | $1.00 \text{ N}$ | $0.0100 \text{ N}\cdot\text{m}$ | **Validated Phase 8 Baseline** |
| **L5** | $1.25 \text{ N}$ | $0.0125 \text{ N}\cdot\text{m}$ | Candidate Test Point |
| **L6** | $1.50 \text{ N}$ | $0.0150 \text{ N}\cdot\text{m}$ | Candidate Upper Bound |

> [!IMPORTANT]
> **Safety Directive**: Candidate load levels are **test points**, NOT mandatory targets. The operator must NOT force the experiment to reach $1.50 \text{ N}$ if safety limits or mechanical instability occur at an earlier force point.

---

## 4. External Torque Calculation & Terminology

### Formula
$$\text{Estimated Applied External Torque } T_{ext} = F_{gauge} \times r_{pulley}$$
- $r_{pulley} = 0.010 \text{ m}$ ($10 \text{ mm}$ effective radius).
- $F_{gauge} = \text{Force gauge reading in Newtons (N)}$.

### Terminology Rules
1. $T_{ext}$ shall be explicitly reported as **"Estimated Applied External Torque"** to reflect physical friction, wrap angle, and slip uncertainties.
2. $T_{ext}$ shall **NOT** be claimed as the exact net internal motor shaft torque unless verified by a calibrated dynamometer.

---

## 5. Experimental Test Procedure

### A. Pre-Trial Dry Run (Motor OFF)
1. Confirm felt strap moves smoothly without catching or binding on the $20 \text{ mm}$ pulley.
2. Confirm pulley set screws are tight on the motor D-shaft.
3. Confirm force gauge is anchored safely with operator clearance $\ge 30 \text{ cm}$.
4. Confirm hardware PC13 E-stop button is accessible to the operator's free hand.

### B. Ascending Force Level Sweep Procedure
Execute load levels in conservative ascending order: **L0 $\rightarrow$ L1 $\rightarrow$ L2 $\rightarrow$ L3 $\rightarrow$ L4 $\rightarrow$ L5 $\rightarrow$ L6**.

For each candidate force level:
1. **Pre-Flight Verification**: System state = `SYSTEM_STATE_DISABLED`, PWM = $0.0\%$, `R_EN`/`L_EN` = $0.00 \text{ V}$, active faults = $0x00$.
2. **Startup**: Transition `DISABLED` $\rightarrow$ `ARMED` $\rightarrow$ `RUNNING` with `target_rpm = 150.0`.
3. **Unloaded Baseline Phase ($0 - 3.0 \text{ s}$)**: Allow motor to reach steady state ($150 \pm 2 \text{ RPM}$).
4. **Disturbance Application ($t = 3.0 \text{ s}$)**: Apply friction strap tension smoothly until the force gauge reads the target candidate force level.
5. **Hold Phase ($3.0 - 7.0 \text{ s}$)**: Maintain constant force for $4.0 \text{ seconds}$.
6. **Smooth Release ($t = 7.0 \text{ s}$)**: Release strap tension smoothly and rapidly without allowing the strap to catch.
7. **Recovery Phase ($7.0 - 10.0 \text{ s}$)**: Observe integral speed recovery back to $150 \pm 3 \text{ RPM}$.
8. **Shutdown**: Issue `STOP` command; verify system transitions to `DISABLED` and PWM $= 0.0\%$.
9. **Cooling Interval**: Allow $30 \text{ seconds}$ cooling period between trials.
10. **Repeatability**: Execute **3 valid repeatability trials** at the given load level before progressing to the next force level.

---

## 6. Conservative Safety Stop Criteria

The operator must **IMMEDIATELY RELEASE THE STRAP AND STOP THE SWEEP** if any of the following occur:

1. **Current Limit Proximity**: Filtered motor current reaches or exceeds $1.50 \text{ A}$ (leaves $0.30 \text{ A}$ margin below the $1.80 \text{ A}$ firmware trip limit).
2. **Stall Warning**: Motor speed drops below $30.0 \text{ RPM}$ during disturbance hold.
3. **Strap Instability**: Strap catches, slips erratically, or begins wrapping around the pulley.
4. **Thermal Warning**: BTS7960 heatsink temperature exceeds $50^\circ\text{C}$ or motor casing exceeds $45^\circ\text{C}$.
5. **Sensor Fault**: INA169 ADC reading drops below $0.01 \text{ V}$ or exceeds $3.10 \text{ V}$.
6. **Encoder Fault**: Quadrature ticks freeze while PWM duty $> 20\%$.
7. **Mechanical Instability**: Pulley slipping on shaft, abnormal vibration, or chatter.

> [!CAUTION]
> - **NEVER** intentionally force the motor into the $1.80 \text{ A}$ firmware over-current threshold.
> - **NEVER** hold a load while the motor approaches stall.

---

## 7. Performance Metrics Definitions

For each trial at every load level, the following metrics must be computed:

### Speed Regulation Metrics
- **$N_{pre}$**: Mean filtered RPM over $t \in [1.0\,\text{s}, 3.0\,\text{s}]$.
- **$N_{min}$**: Minimum filtered RPM during disturbance hold ($t \in [3.0\,\text{s}, 7.0\,\text{s}]$).
- **$\Delta N_{drop}$**: Absolute speed drop ($N_{pre} - N_{min}$ in RPM).
- **$\% \Delta N$**: Percentage speed drop ($\frac{\Delta N_{drop}}{150.0} \times 100\%$).
- **$N_{overshoot,rel}$**: Peak speed overshoot above $150 \text{ RPM}$ after strap release ($t \in [7.0\,\text{s}, 8.5\,\text{s}]$).
- **$t_{rec}$**: Recovery time from strap release ($t = 7.0 \text{ s}$) until filtered RPM re-enters and remains within $150 \pm 3.0 \text{ RPM}$ ($\pm 2.0\%$).
- **$SSE_{post}$**: Post-disturbance steady-state error (mean error over $t \in [8.5\,\text{s}, 10.0\,\text{s}]$).

### Control Effort & Electrical Metrics
- **$PWM_{pre}$**: Unloaded steady-state PWM duty cycle.
- **$PWM_{peak}$**: Maximum PWM duty cycle commanded during disturbance hold.
- **$\Delta PWM$**: Control effort increase ($PWM_{peak} - PWM_{pre}$).
- **$I_{pre}$**: Unloaded steady-state motor current.
- **$I_{peak}$**: Maximum motor current measured during disturbance hold.
- **$\Delta I$**: Electrical current increase ($I_{peak} - I_{pre}$).

---

## 8. Telemetry & Data Logging Specification

All trial data shall be logged to `analysis/data/disturbance_sweep_150rpm.csv` at $100 \text{ Hz}$ ($10 \text{ ms}$ sampling).

### Log Schema (`analysis/data/disturbance_sweep_150rpm.csv`)

| Column Header | Data Type | Description |
|:---|:---:|:---|
| `run_id` | `uint8_t` | Trial number ($1, 2, 3$) for the current load level |
| `load_level_id` | `string` | Load identifier (`L0` to `L6`) |
| `timestamp_ms` | `uint32_t` | Control loop timestamp in milliseconds |
| `target_rpm` | `float` | Commanded setpoint ($150.0 \text{ RPM}$) |
| `raw_encoder_count` | `int32_t` | 32-bit TIM2 hardware encoder count |
| `raw_speed_rpm` | `float` | Single-sample calculated RPM |
| `filtered_speed_rpm` | `float` | 3-sample moving average RPM |
| `pwm_duty_percent` | `float` | Command duty cycle ($0.0\%$ to $100.0\%$) |
| `current_a` | `float` | Filtered motor current from INA169 |
| `applied_force_n` | `float` | Manually recorded force gauge reading in Newtons |
| `estimated_external_torque_nm` | `float` | Calculated torque $T_{ext} = F \cdot 0.010 \text{ m}$ |
| `disturbance_state` | `uint8_t` | `0`=Pre-load, `1`=Disturbance Active, `2`=Recovery |
| `system_state` | `uint8_t` | State machine state (`3` = RUNNING) |
| `fault_flags` | `uint32_t` | Active fault bitmask ($0x00$ = None) |

---

## 9. Required Plot Artifacts

The analysis phase will produce 5 designated plot artifacts in `analysis/plots/`:

1. **`disturbance_sweep_150rpm.png`**: Multi-panel transient speed, PWM duty, and current time-series traces for all load levels.
2. **`load_vs_speed_drop.png`**: $X$-axis = $T_{ext}$ ($\text{N}\cdot\text{m}$), $Y$-axis = Percentage Speed Drop ($\% \Delta N$).
3. **`load_vs_recovery_time.png`**: $X$-axis = $T_{ext}$ ($\text{N}\cdot\text{m}$), $Y$-axis = Recovery Time $t_{rec}$ ($\text{ms}$).
4. **`load_vs_peak_current.png`**: $X$-axis = $T_{ext}$ ($\text{N}\cdot\text{m}$), $Y$-axis = Peak Current $I_{peak}$ ($\text{A}$).
5. **`load_vs_peak_pwm.png`**: $X$-axis = $T_{ext}$ ($\text{N}\cdot\text{m}$), $Y$-axis = Peak PWM Duty $PWM_{peak}$ ($\%$).

---

## 10. Repeatability & Statistical Analysis

- **Sample Size**: Exactly 3 valid trials per load level.
- **Statistical Outputs**: For each load level, compute Mean, Min, Max, and Standard Deviation for $\% \Delta N$, $t_{rec}$, $I_{peak}$, and $PWM_{peak}$.
- **Invalidation Rule**: A trial may ONLY be declared invalid if an explicit procedural or instrumentation failure occurred (e.g. strap slippage or force gauge misread). Outlier data from valid trials must be retained.

---

## 11. Controller Decision & Evaluation Criteria

The disturbance-rejection envelope shall be evaluated against the following analytical criteria:

1. **Control Response & Linearity**: Analyze how PWM duty ($\Delta PWM$) and current ($\Delta I$) increase with applied load torque ($T_{ext}$). Treat this as a trend to investigate (which may be non-linear due to friction, gearbox dynamics, and saturation) rather than a rigid linear constraint.
2. **Integral Convergence**: Verify that post-disturbance steady-state error returns to $0.00 \text{ RPM}$ across all safe load levels.
3. **Controllable Boundary Characterization**: Observe recovery time ($t_{rec}$) and speed drop ($\% \Delta N$) across load levels. A sudden change in behavior is an important experimental indicator of saturation or boundary of the controllable envelope.
4. **Safety Margin**: Confirm that peak current remains strictly below the $1.50 \text{ A}$ experimental abort threshold across all completed points.

---

## 12. HIL Comparison Methodology

1. Physical disturbance-rejection trends ($\% \Delta N$, $t_{rec}$, $I_{peak}$, $PWM_{peak}$) will be compared against virtual HIL simulation disturbance responses at matching external torque levels ($T_{ext}$).
2. Discrepancies between HIL predictions and physical measurements shall be explicitly documented.

---

## 13. STOP Condition Confirmation

Protocol design is **100% COMPLETE**.

> [!IMPORTANT]
> **STOP CONDITION CONFIRMED**:
> - Physical motor operation for Phase 9 has **NOT** been performed.
> - Mechanical loads have **NOT** been applied.
> - Firmware and controller gains remain **UNMODIFIED**.
> - The system remains safely in `SYSTEM_STATE_DISABLED` with $0.0\%$ PWM.
