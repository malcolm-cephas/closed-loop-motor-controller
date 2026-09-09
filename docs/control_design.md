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
*Note: These parameters do not represent the final purchased hardware. They are estimates to validate the PI logic in simulation.*
