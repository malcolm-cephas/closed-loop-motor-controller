# Phase 8 — Physical Load-Disturbance Test Protocol

## Executive Overview
This document specifies the safety, mechanical, procedural, and telemetry protocols for evaluating physical closed-loop load-disturbance rejection on the DC motor controller at **150 RPM**. 

This protocol ensures that physical mechanical drag is applied safely, repeatably, and measurably without stalling the motor, exceeding current trip limits, or compromising operator safety.

---

## 1. Mechanical Arrangement & Setup

### Hardware Configuration
- **Motor**: JGA25-370 12 V DC gear motor with 1496 PPR Hall quadrature encoder.
- **Mounting**: Rigidly clamped to an aluminum test fixture on the bench.
- **Output Shaft**: $6\,\text{mm}$ D-shaft fitted with a lightweight $20\,\text{mm}$ diameter smooth aluminum pulley ($r = 10\,\text{mm} = 0.010\,\text{m}$).
- **Friction Mechanism**: Adjustable felt/leather friction strap wrapped $180^\circ$ around the pulley perimeter.
- **Tension Control**: Fixed anchor on one end of the strap; manual calibrated spring scale / force gauge on the tension end.
- **Safety Clearance**: The operator operates the tension lever / spring scale from a designated safe position $30\,\text{cm}$ away from the rotating pulley. The physical PC13 E-stop button remains completely unobstructed and immediately accessible.

### ASCII Setup Diagram

```text
               ┌─────────────────────────────────────────┐
               │         BENCH TEST FIXTURE              │
               │                                         │
               │   ┌───────────────┐     ┌───────────┐   │
               │   │ JGA25-370     │═══╤═│ 20mm      │   │
               │   │ DC Motor      │   │ │ Pulley    │   │
               │   └───────────────┘   │ └─────┬─────┘   │
               └───────┬───────────────┴───────┼─────────┘
                       │                       │
                       │           ┌───────────┴───────────┐
                       ▼           │ Felt Friction Strap   │
                ┌─────────────┐    └───────────┬───────────┘
                │ NUCLEO Board│                │
                │ PC13 E-Stop │                ▼
                └─────────────┘       ┌─────────────────┐
                      ▲               │ Force Gauge /   │
                      │               │ Spring Scale    │
                      └───────────────┴─────────────────┘
                       (Operator Safety Position)
```

---

## 2. Disturbance Definition & Timing Profile

- **Operating Target**: $150.0 \text{ RPM}$
- **Pre-Disturbance Phase ($0 - 3.0 \text{ s}$)**: System reaches steady state at $150 \text{ RPM}$ under unloaded baseline condition ($8.8\%$ PWM, $0.035 \text{ A}$).
- **Disturbance Application ($t = 3.0 \text{ s}$)**: Operator smoothly applies tension to the friction strap, introducing a bounded mechanical drag.
- **Disturbance Hold Phase ($3.0 - 7.0 \text{ s}$)**: Drag maintained constantly for $4.0 \text{ seconds}$.
- **Pre-Trial Dry Run (Motor OFF)**:
  - Verify strap cannot catch on pulley.
  - Verify pulley remains secure on output D-shaft.
  - Verify strap can be applied and released smoothly and rapidly without shock.
  - Verify force gauge can be read safely from $\ge 30\,\text{cm}$ clearance.
  - Verify free hand reaches PC13 E-stop button immediately.

- **Disturbance Release ($t = 7.0 \text{ s}$)**: Operator releases strap tension smoothly and rapidly without allowing the strap to catch.
- **Post-Disturbance Observation ($7.0 - 10.0 \text{ s}$)**: System observed for $3.0 \text{ seconds}$ to measure integral recovery and return to steady state.

```text
Target Speed ───► 150 RPM ─────────────────────────────────────────────
Speed (RPM)       ┌───────────┐       Recovery       ┌─────────────┐
                  │ Pre-      │◄── Drop ──►┌─────────┤ Post-       │
                  │ Load      │            │ Drag    │ Load        │
                  └───────────┘            └─────────┴─────────────┘
Time (s):         0.0        3.0          7.0       10.0
State:            ─── RUNNING ──────────────────────────────────────
```

---

## 3. Repeatability Procedure (3 Physical Trials)

The physical disturbance test consists of **3 identical repeatability trials**:

1. **Pre-Flight Inspection**:
   - Verify system state is `SYSTEM_STATE_DISABLED`.
   - Verify PWM output is $0.0\%$.
   - Confirm BTS7960 `R_EN`/`L_EN` measured $0.00 \text{ V}$.
   - Confirm encoder count is stable ($0$ drift at rest).
   - Confirm INA169 current reading is $0.02 \text{ V}$ ($0.00 \text{ A}$).
   - Verify hardware PC13 E-stop is armed and accessible.

2. **Trial Execution Sequence** (Repeat for Trials 1, 2, and 3):
   - Transition `DISABLED` $\rightarrow$ `ARMED` $\rightarrow$ `RUNNING` with `target_rpm = 150.0`.
   - Run unloaded for $3.0 \text{ s}$ until steady state is established ($150 \pm 2.0 \text{ RPM}$).
   - At $t = 3.0 \text{ s}$, smoothly apply friction strap tension to generate bounded drag.
   - Maintain constant tension for $4.0 \text{ s}$ (until $t = 7.0 \text{ s}$).
   - At $t = 7.0 \text{ s}$, instantly release strap tension.
   - Observe speed recovery for $3.0 \text{ s}$ (until $t = 10.0 \text{ s}$).
   - Issue `STOP` command; transition system to `SYSTEM_STATE_DISABLED`.
   - Verify PWM returns to $0.0\%$ and inspect fault flags (`FAULT_NONE`).
   - Allow $30 \text{ seconds}$ cooling period between trials.

3. **Repeatability Acceptance Criteria**:
   - Speed drop under disturbance across the 3 trials must agree within $\pm 10\%$.
   - Speed recovery time back to $150 \pm 3 \text{ RPM}$ across trials must agree within $\pm 30 \text{ ms}$.

---

## 4. Telemetry Specification & Log Format

Telemetry is logged continuously at the $100 \text{ Hz}$ control loop rate ($10 \text{ ms}$ sample interval). 

### Required Telemetry Fields

| Field Name | Type | Unit | Description |
|:---|:---:|:---:|:---|
| `timestamp_ms` | `uint32_t` | $\text{ms}$ | Control loop timestamp |
| `target_rpm` | `float` | $\text{RPM}$ | Commanded speed setpoint ($150.0$) |
| `raw_encoder_count` | `int32_t` | counts | Cumulative 32-bit TIM2 encoder count |
| `raw_speed` | `float` | $\text{RPM}$ | 1-sample discrete speed calculation |
| `filtered_speed` | `float` | $\text{RPM}$ | 3-sample moving average speed |
| `error_rpm` | `float` | $\text{RPM}$ | Speed error (`target_rpm` $-$ `filtered_speed`) |
| `pi_output` | `float` | $\%$ | PI controller output before safety clamping |
| `pwm_duty` | `float` | $\%$ | Final PWM duty cycle delivered to BTS7960 |
| `motor_current` | `float` | $\text{A}$ | INA169 filtered current measurement |
| `system_state` | `uint8_t` | enum | State Machine state (`3` = RUNNING) |
| `fault_flags` | `uint32_t` | bitmask | Active fault flags ($0x00$ = None) |
| `event_marker` | `uint8_t` | enum | `0`=Unloaded, `1`=Disturbance Active, `2`=Recovery |

---

## 5. Performance Metrics Definitions

For each trial, the following performance metrics are calculated:

1. **Pre-Disturbance Mean Speed ($N_{pre}$)**: Mean `filtered_speed` over $t \in [1.0\,\text{s}, 3.0\,\text{s}]$.
2. **Minimum Speed Under Disturbance ($N_{min}$)**: Minimum `filtered_speed` recorded during $t \in [3.0\,\text{s}, 7.0\,\text{s}]$.
3. **Maximum Speed Drop ($\Delta N_{drop}$)**:
   $$\Delta N_{drop} = N_{pre} - N_{min} \quad (\text{RPM})$$
4. **Percentage Speed Drop ($\% \Delta N$)**:
   $$\% \Delta N = \left( \frac{\Delta N_{drop}}{150.0} \right) \times 100\%$$
5. **Peak Disturbance Current ($I_{peak,dist}$)**: Maximum `motor_current` measured during $t \in [3.0\,\text{s}, 7.0\,\text{s}]$.
6. **Peak Disturbance PWM ($PWM_{peak,dist}$)**: Maximum `pwm_duty` commanded during $t \in [3.0\,\text{s}, 7.0\,\text{s}]$.
7. **Speed Recovery Time ($t_{rec}$)**: Time elapsed from disturbance release ($t = 7.0\,\text{s}$) until `filtered_speed` enters and remains within $150 \pm 3.0 \text{ RPM}$ ($\pm 2.0\%$).
8. **Post-Disturbance Excursion ($N_{overshoot,rel}$)**: Peak speed overshoot above $150 \text{ RPM}$ following disturbance release.
9. **Post-Disturbance Steady-State Error ($SSE_{post}$)**: Mean speed error over $t \in [8.5\,\text{s}, 10.0\,\text{s}]$.

---

## 6. Safety Limits & Stop Conditions

The experiment must be **IMMEDIATELY STOPPED** by pressing the PC13 E-stop or issuing a forced cutoff if any of the following conservative safety criteria are met:

1. **Over-Current Proximity**: Motor current exceeds $1.50 \text{ A}$ (approaching the $1.80 \text{ A}$ software trip limit).
2. **Stall Warning**: Speed drops below $30.0 \text{ RPM}$ during disturbance application.
3. **Thermal Limit**: BTS7960 heatsink temperature exceeds $50^\circ\text{C}$ or motor casing exceeds $45^\circ\text{C}$.
4. **Sensor Fault**: Current sensor voltage drops below $0.01 \text{ V}$ or exceeds $3.10 \text{ V}$.
5. **Encoder Fault**: Delta counts equal zero for $> 100 \text{ ms}$ while PWM duty $> 20\%$.
6. **Mechanical Slippage / Catching**: Friction strap catches, jerks, or slips erratically.
7. **Uncontrolled Vibration / Noise**: Abnormal audible chatter or mechanical resonance.

> [!CAUTION]
> **NEVER** intentionally stall the motor, lock the pulley, or drive current into the $1.80 \text{ A}$ trip limit.

---

## 7. Disturbance Torque Characterization Method

### Method A — Direct Independent Measurement (If Force Gauge Available)
If a spring scale / force gauge is attached to the friction strap end:
$$\text{Torque } \tau_{load} = F_{gauge} \times r_{pulley}$$
- Pulley radius $r = 0.010 \text{ m}$ ($10 \text{ mm}$).
- Measured force $F_{gauge}$ (e.g. $1.0 \text{ N}$ force $\rightarrow \tau_{load} = 0.010 \text{ N}\cdot\text{m}$).

### Method B — Unquantified Bounded Drag (If Force Gauge Unavailable)
If no spring scale is available, the disturbance shall be documented as **"Bounded Friction Drag (Unquantified)"**. 
- It shall **NOT** be assigned an assumed numerical torque value (such as $0.01 \text{ N}\cdot\text{m}$).
- The magnitude shall be characterized by electrical/control effort metrics ($\Delta PWM$ increase, $\Delta I$ current increase).

---

## 8. Unloaded Baseline Reference (Phase 7 Physical Results)

The physical disturbance trial results will be compared against the validated Phase 7 unloaded $150 \text{ RPM}$ baseline:

| Metric | Unloaded Baseline (Phase 7) |
|:---|:---:|
| **Target Speed** | $150.0 \text{ RPM}$ |
| **Rise Time (10% to 90%)** | $20.0 \text{ ms}$ |
| **Peak Speed / Overshoot** | $176.5 \text{ RPM}$ ($17.65\%$) |
| **Settling Time ($\pm 2\%$)** | $150.0 \text{ ms}$ |
| **Steady-State Error** | $0.00 \text{ RPM}$ |
| **Steady-State Current** | $0.035 \text{ A}$ ($35 \text{ mA}$) |
| **Maximum Peak Current** | $1.17 \text{ A}$ (transient startup) |
| **Steady-State PWM Duty** | $8.8\%$ |
| **Maximum PWM Duty** | $97.5\%$ (transient startup) |
| **Active Fault Flags** | `FAULT_NONE` ($0x00$) |

---

## 9. HIL Comparison Strategy

1. **Normalized Response Comparison**: Physical speed drop ($\% \Delta N$) and recovery time ($t_{rec}$) will be compared normalized against HIL simulation disturbance trends.
2. **Current & Duty Step Match**: Compare the physical $\Delta PWM$ and $\Delta I$ step increases against HIL virtual load steps.
3. **No False Torque Equivalency**: If physical torque is unmeasured (Method B), physical results will **NOT** be claimed as an exact $0.01 \text{ N}\cdot\text{m}$ match to HIL.

---

## 10. Additional Measurement Equipment Recommendations

To materially improve disturbance quantification for Phase 8 physical trials, the following simple bench tools are recommended:

1. **Small Mechanical Spring Scale / Force Gauge ($0 - 5 \text{ N}$ range)**: To measure friction strap tension force $F$ and calculate exact torque $\tau = F \cdot r$.
2. **Digital Non-Contact Infrared Thermometer**: To monitor BTS7960 MOSFET and motor casing thermal buildup.
