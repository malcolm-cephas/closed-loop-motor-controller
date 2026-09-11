# Control System Design

## 1. PI Controller Architecture
- Purely hardware-independent discrete-time implementation.
- **Anti-Windup**: Conditional integration. The integral term accumulation is paused if the output is saturated in the direction of the error.
- **Output Saturation**: Clamped between configurable min/max bounds before being returned to the safety layer.

## 2. Speed Estimation
The `speed_estimator` module is configurable with:
- `counts_per_output_revolution`
- `measurement_period`

It supports both positive and negative directions (signed RPM). The exact counts/revolution must be experimentally calibrated rather than hard-coding vendor claims (e.g., assuming 11 PPR).

## 3. Current Monitoring
The `current_monitor` applies a first-order IIR low-pass filter (configurable alpha) to raw ADC values and applies a scalable offset and gain.

## 4. Simulation Assumptions (Python Model)
A physical DC motor model was implemented in Python (`analysis/scripts/motor_sim.py`) with the following equations:
- **Electrical**: $I = (V - K_e \cdot \omega) / R$ (Simplified steady-state assumption)
- **Mechanical**: $J \cdot \frac{d\omega}{dt} = K_t \cdot I - B \cdot \omega - T_{load}$

**Assumptions**:
- Resistance $R = 5.0 \, \Omega$
- Inductance $L = 0.005 \, H$
- Motor Constants $K_e = K_t = 0.02$
- Rotor Inertia $J = 0.0001 \, kg\cdot m^2$
- Viscous Friction $B = 0.00005$
*Note: These parameters do not represent the final purchased hardware. They were initial estimates to validate the PI logic in simulation.*

## 5. Physical Plant Identification & Retuned PI Parameters (Phase 6A)
Based on Phase 5 empirical open-loop characterization data, the physical motor and driver parameters were identified:

- **Empirical Gain ($K_{plant}$)**: $\approx 2.66 \text{ RPM}/\%$ duty cycle ($248.5 \text{ RPM}$ at $100\%$ duty, $128.8 \text{ RPM}$ at $50\%$ duty).
- **Dead Zone**: $\approx 10\%$ startup threshold ($0 \text{ RPM}$ at $10\%$ duty, reliable movement starts at $15\%$ duty / $18.5 \text{ RPM}$).
- **Time Constant ($\tau$)**: $\approx 100 \text{ ms}$ (steady-state acceleration achieved in $\sim 250 \text{ ms}$).
- **Refined Motor Model Parameters**:
  - Armature Resistance ($R$): $10.0 \, \Omega$
  - Torque & Back-EMF Constant ($K_t = K_e$): $0.045 \, \text{N}\cdot\text{m/A}$ / $\text{V}/(\text{rad/s})$
  - Rotor Inertia ($J$): $0.00005 \, \text{kg}\cdot\text{m}^2$
  - Viscous Friction ($B$): $0.0001 \, \text{N}\cdot\text{m}\cdot\text{s/rad}$
  - Stiction Torque ($T_{stiction}$): $0.005 \, \text{N}\cdot\text{m}$ (modeling $10\%$ dead zone)

### Retuned PI Controller Gains
## 6. Speed Estimator Refinement & Feedback Delay Analysis (Phase 6D)

### Feedback Quantization Analysis
- **Encoder Resolution**: $1496 \text{ counts / output revolution}$.
- **Sampling Period ($dt$)**: $10 \text{ ms}$ ($100 \text{ Hz}$).
- **Single-Tick Quantization Step**:
  $$\text{RPM}_{step} = \frac{1 \text{ tick}}{1496 \text{ counts/rev} \times 0.01 \text{ s}} \times 60 \text{ s/min} = 4.0107 \text{ RPM}$$
- **Feedback Noise**: Raw 1-sample speed feedback exhibits $\pm 4.01 \text{ RPM}$ ($\pm 4.01\%$) discrete quantization ripple.

### Estimator Candidate Comparison

| Estimator Variant | Count Window | Moving Average Window | Group Delay | Noise Reduction | Transient Distortion |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Estimator A (Existing)** | $10 \text{ ms}$ | 1 (Raw) | $0 \text{ ms}$ | $0\%$ | None |
| **Estimator B (3-Sample MA)** | $10 \text{ ms}$ | 3 samples | $10 \text{ ms}$ | $\sim 67\%$ | Negligible |
| **Estimator B (5-Sample MA)** | $10 \text{ ms}$ | 5 samples | $20 \text{ ms}$ | $\sim 80\%$ | Slight smoothing |
| **Estimator C (30 ms Window)** | $30 \text{ ms}$ | N/A | $10 \text{ ms}$ | $\sim 67\%$ | Phase lag |

### Estimator Selection Rationale
- **Selected Estimator**: **Estimator B (3-Sample Moving Average)** for telemetry filtering and closed-loop feedback smoothing.
- **Rationale**: 
  1. Reduces single-tick feedback ripple from $\pm 4.01 \text{ RPM}$ to $\pm 1.34 \text{ RPM}$.
  2. Introduces minimal effective transport delay ($10 \text{ ms}$ group delay), preserving phase margin and control loop stability.
  3. Low CPU computational overhead on STM32 Cortex-M4.

### Final Candidate Gains Retention
- **Retained Gains**: $K_p = 0.5, K_i = 15.0$
- **Verification**: Evaluated via physical 100 RPM closed-loop tests ($10.0 \text{ ms}$ rise time, $140.0 \text{ ms}$ filtered settling time, $-0.01 \text{ RPM}$ SSE) and verified 100% PASS across the complete 9-scenario HIL test suite.


