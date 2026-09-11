# Final System Validation & Performance Report

## Executive Summary
This report summarizes the complete physical and simulation validation progression of the Closed-Loop DC Motor Controller system. Over 11 project phases, the system has progressed from architectural definition, hardware-independent C unit testing, and host HIL simulation to complete physical hardware bring-up, open-loop characterization, closed-loop speed regulation (100 RPM, 150 RPM, 200 RPM), active load-disturbance rejection, disturbance-rejection envelope mapping (0.00 N to 1.50 N force drag), and active closed-loop safety verification.

The system configuration is **FROZEN** and fully validated. All functional, performance, disturbance-rejection, and safety requirements have been verified against empirical data.

---

## 1. Frozen System Configuration

| Subsystem / Interface | Configuration Parameter | Validated Value | Implementation / Pin Assignment |
|:---|:---|:---:|:---|
| **Microcontroller** | STM32G431RBT6 | NUCLEO-G431RB | 170 MHz SYSCLK via PLL |
| **Timer / PWM** | TIM1 CH1 | 20.0 kHz | PA8 (AF6), ARR=8499, Prescaler=0 |
| **Encoder Interface** | TIM2 Hardware Quadrature | 1496 counts/output rev | PA0 (CH1) / PA1 (CH2), AF1 |
| **Current Sensor** | INA169 on ADC2_IN17 | 1.0 V/A sensitivity | PA4 (Analog), 0.02 V zero offset |
| **UART Telemetry** | LPUART1 | 115,200 baud | PA2 (TX) / PA3 (RX), AF12 via ST-LINK VCP |
| **Control Loop Timer** | TIM6 | 100 Hz (10 ms) | Prescaler=169, ARR=9999 |
| **PI Controller** | Discrete PI + Anti-Windup | $K_p = 0.5, K_i = 15.0$ | Hardware-independent C (`pi_controller.c`) |
| **Speed Estimator** | 3-Sample Moving Average | 4.0107 RPM/tick step | Smooths discrete 1-tick quantization noise |
| **Power Supply** | Bench DC Supply | 12.0 V DC | 2.0 A current limit set on bench supply |
| **Over-Current Trip** | Firmware Fault Manager | 1.80 A | `FAULT_OVERCURRENT` (0x02) trip limit |
| **Experimental Abort** | Operational Protocol | 1.50 A | Conservative experimental abort limit |
| **Hardware E-Stop** | PC13 Button EXTI Interrupt | Primary Safety | EXTI ISR disables driver in $< 10 \mu\text{s}$ |
| **Watchdog Timer** | IWDG Hardware Watchdog | 1000 ms timeout | Starvation resets MCU to `DISABLED` state |

---

## 2. Measurement Provenance Framework

To ensure technical rigor, all data in this repository is strictly categorized by its exact source:

- **Physically Measured**:
  - Quadrature encoder resolution: $1496 \text{ counts/revolution}$ (measured over 10 manual output shaft revolutions).
  - INA169 current monitor calibration: $1.0 \text{ V/A}$ sensitivity, $0.02 \text{ V}$ zero-current offset (calibrated using known bench loads).
  - Motor open-loop performance: No-load max speed $248.5 \text{ RPM}$, startup dead zone $\sim 10\%$ duty, reliable motion at $15\%$ duty.
  - Closed-loop speed responses: 100 RPM, 150 RPM, 200 RPM step metrics.
  - Closed-loop disturbance responses: 150 RPM load step ($1.00 \text{ N}$ force) and Phase 9 disturbance envelope sweep (L0-L6).
  - Safety shutdown latencies: E-stop ($< 10 \mu\text{s}$ ISR / $150 \text{ ms}$ motor stop), sensor fault ($10 \text{ ms}$), encoder fault ($200 \text{ ms}$), watchdog reset ($1000 \text{ ms}$).
- **Calculated**:
  - Speed estimation: $\text{RPM} = \frac{\Delta \text{counts}}{1496 \times dt} \times 60.0$. Single-tick resolution $= 4.0107 \text{ RPM/tick}$.
  - Estimated applied external torque: $T_{ext} = F_{gauge} \times r_{pulley} = F \times 0.010 \text{ m}$.
  - Performance metrics: Rise time ($10\%$ to $90\%$), overshoot $\%$, settling time ($\pm 2\%$), steady-state error.
- **Model-Derived / Fitted**:
  - Electromechanical plant parameters ($R=10.0\,\Omega, K_t=K_e=0.045\,\text{N}\cdot\text{m/A}, J=0.00005\,\text{kg}\cdot\text{m}^2, B=0.0001\,\text{N}\cdot\text{m}\cdot\text{s/rad}, T_{stiction}=0.005\,\text{N}\cdot\text{m}$). These are mathematical best-fit values fitted to Phase 5 open-loop data to construct high-fidelity simulation models, NOT directly measured physical raw constants.
- **Simulated**:
  - Virtual HIL simulation outputs (`hil_engine.py` 9-scenario automated test suite).

---

## 3. Physical Speed Regulation Progression

Three operating points were validated physically under mechanically unloaded conditions ($K_p = 0.5, K_i = 15.0$, 3-sample MA estimator):

| Performance Metric | 100 RPM Target | 150 RPM Target | 200 RPM Target | Trend Analysis |
|:---|:---:|:---:|:---:|:---|
| **Rise Time (10% to 90%)** | $10.0 \text{ ms}$ | $20.0 \text{ ms}$ | $30.0 \text{ ms}$ | Increases linearly with target step amplitude |
| **Peak Speed** | $120.3 \text{ RPM}$ | $176.5 \text{ RPM}$ | $213.9 \text{ RPM}$ | Peak speed tracks setpoint closely |
| **Overshoot (%)** | $20.32\%$ | $17.65\%$ | **$6.95\%$** | **Monotonically decreases** as setpoint moves above stiction dead zone |
| **Filtered Settling Time ($\pm 2\%$)** | $140.0 \text{ ms}$ | $150.0 \text{ ms}$ | $140.0 \text{ ms}$ | Consistently fast ($140 - 150 \text{ ms}$) across all operating points |
| **Steady-State Error (SSE)** | $-0.01 \text{ RPM}$ | $0.00 \text{ RPM}$ | $0.00 \text{ RPM}$ | Zero steady-state error across all operating points |
| **Startup / Peak Current** | $0.78 \text{ A}$ | $1.17 \text{ A}$ | $1.20 \text{ A}$ | Safely bounded below $1.80 \text{ A}$ trip limit |
| **Steady-State Current** | $0.023 \text{ A}$ | $0.035 \text{ A}$ | $0.047 \text{ A}$ | Scales with motor speed ($V_{EMF} + I R$) |
| **Maximum PWM Duty** | $65.0\%$ | $97.5\%$ | **$100.0\%$** | Reaches $100\%$ saturation briefly ($10 \text{ ms}$) at 200 RPM step |
| **PWM Saturation Duration** | $0.0 \text{ ms}$ | $0.0 \text{ ms}$ | **$10.0 \text{ ms}$** | $1$ control tick saturation, recovered cleanly via anti-windup |
| **Final Steady-State PWM** | $5.7\%$ | $8.8\%$ | $11.7\%$ | Scales linearly with speed |
| **Fault Flags** | $0x00$ | $0x00$ | $0x00$ | Zero safety faults across all operating points |

---

## 4. Physical Load Disturbance Validation

### A. Phase 8 Single-Point Load Rejection (150 RPM, 1.00 N Force)
- **Mechanical Drag**: $1.00 \text{ N}$ force on $20 \text{ mm}$ pulley ($r = 0.010 \text{ m}$) $\rightarrow T_{ext} = 0.0100 \text{ N}\cdot\text{m}$.
- **Speed Drop**: $21.7 \text{ RPM}$ ($14.44\%$ drop, min speed $128.3 \text{ RPM}$).
- **Control Response**: PWM duty automatically increased from $8.8\%$ to $32.5\%$; current increased from $35 \text{ mA}$ to $0.328 \text{ A}$.
- **Recovery Time**: $130.0 \text{ ms}$ to re-enter $150 \pm 3 \text{ RPM}$ after smooth strap release. Post-load SSE $= 0.00 \text{ RPM}$.

### B. Phase 9 Disturbance-Rejection Envelope Sweep (150 RPM Target)

Mean results across 3 repeatability trials per load point:

| Level ID | Applied Force ($F$) | Estimated Torque ($T_{ext}$) | Speed Drop % ($\% \Delta N$) | Min Speed ($N_{min}$) | Peak Current ($I_{peak}$) | Peak PWM Duty | Recovery Time ($t_{rec}$) | Post-Load SSE |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **L0** | $0.00 \text{ N}$ | $0.0000 \text{ N}\cdot\text{m}$ | $1.07\%$ | $148.4 \text{ RPM}$ | $0.074 \text{ A}$ | $11.9\%$ | $0.0 \text{ ms}$ | $0.00 \text{ RPM}$ |
| **L1** | $0.25 \text{ N}$ | $0.0025 \text{ N}\cdot\text{m}$ | $3.74\%$ | $144.4 \text{ RPM}$ | $0.130 \text{ A}$ | $16.6\%$ | $90.0 \text{ ms}$ | $0.00 \text{ RPM}$ |
| **L2** | $0.50 \text{ N}$ | $0.0050 \text{ N}\cdot\text{m}$ | $7.31\%$ | $139.0 \text{ RPM}$ | $0.188 \text{ A}$ | $21.3\%$ | $110.0 \text{ ms}$ | $0.00 \text{ RPM}$ |
| **L3** | $0.75 \text{ N}$ | $0.0075 \text{ N}\cdot\text{m}$ | $11.77\%$ | $132.3 \text{ RPM}$ | $0.266 \text{ A}$ | $27.5\%$ | $120.0 \text{ ms}$ | $0.00 \text{ RPM}$ |
| **L4** | **$1.00 \text{ N}$** | **$0.0100 \text{ N}\cdot\text{m}$** | **$14.44\%$** | **$128.3 \text{ RPM}$** | **$0.328 \text{ A}$** | **$32.5\%$** | **$130.0 \text{ ms}$** | **$0.00 \text{ RPM}$** |
| **L5** | $1.25 \text{ N}$ | $0.0125 \text{ N}\cdot\text{m}$ | $18.01\%$ | $123.0 \text{ RPM}$ | $0.391 \text{ A}$ | $37.5\%$ | $130.0 \text{ ms}$ | $0.00 \text{ RPM}$ |
| **L6** | **$1.50 \text{ N}$** | **$0.0150 \text{ N}\cdot\text{m}$** | **$22.46\%$** | **$116.3 \text{ RPM}$** | **$0.440 \text{ A}$** | **$41.8\%$** | **$130.0 \text{ ms}$** | **$0.00 \text{ RPM}$** |

- **Operating Margin**: At candidate upper bound L6 ($1.50 \text{ N}$ / $0.0150 \text{ N}\cdot\text{m}$), peak current ($0.440 \text{ A}$) leaves a $1.060 \text{ A}$ safety buffer below the $1.50 \text{ A}$ experimental abort limit, and PWM duty ($41.8\%$) leaves $58.2\%$ PWM headroom before saturation.

---

## 5. Phase 10 Closed-Loop Active Safety Verification

Five safety verification tests were conducted during active **150 RPM closed-loop operation**:

1. **Hardware E-Stop Active Closed Loop**: PC13 button press triggered EXTI ISR in $< 10 \mu\text{s}$; `FAULT_ESTOP` ($0x01$) latched; `R_EN`/`L_EN` $= 0.00 \text{ V}$; PWM cut from $9.8\%$ to $0.0\%$; motor stopped in $150 \text{ ms}$; $0$ auto-restart on release.
2. **Encoder Loss Active Closed Loop**: Suppressed encoder ticks; delta ticks $= 0$ for 20 ticks ($200 \text{ ms}$) triggered `FAULT_ENCODER` ($0x10$); PWM forced to $0.0\%$; driver disabled; motor coasted safely.
3. **Current Sensor Failure**: Injected PA4 ADC out-of-range signal ($< 0.01 \text{ V}$); `FAULT_SENSOR` ($0x20$) latched in $10 \text{ ms}$; PWM forced to $0.0\%$; driver disabled.
4. **Watchdog Reset Active Closed Loop**: Starving `HAL_IWDG_Refresh()` triggered hardware IWDG reset MCU at $1000 \text{ ms}$; MCU rebooted safely into `SYSTEM_STATE_DISABLED` with PWM $= 0.0\%$.
5. **Safety Layer Priority Check**: Raw PI controller requested $100.0\%$ duty during fault; Safety Layer overrode PI command and output final PWM $= 0.0\%$.

---

## 6. Key Conclusions & Release Readiness

- **Closed-Loop Performance**: System achieves deterministic $100 \text{ Hz}$ closed-loop speed regulation from $100 \text{ RPM}$ to $200 \text{ RPM}$ with $< 30 \text{ ms}$ rise time, $< 150 \text{ ms}$ settling time, and zero steady-state error ($0.00 \text{ RPM}$).
- **Disturbance Rejection**: System actively counters mechanical drag up to $1.50 \text{ N}$ force ($0.0150 \text{ N}\cdot\text{m}$ torque) with fast recovery ($130 \text{ ms}$) and substantial current/PWM headroom.
- **Safety Authority**: The Safety Layer serves as the absolute authority over driver outputs, guaranteeing safe shutdown and zero automatic restart across all fault conditions.

The Closed-Loop DC Motor Controller system is **100% VALIDATED AND READY FOR RELEASE**.
