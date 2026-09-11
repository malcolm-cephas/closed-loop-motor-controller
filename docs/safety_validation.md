# Safety Validation Requirements

This document records the physical safety and fault validation results for the Closed Loop Motor Controller system prior to enabling physical closed-loop speed control.

## Safety Requirements & Validation Matrix

| Requirement | Test | Result | Evidence |
|:---|:---|:---:|:---|
| **E-stop disables motor** | Physical E-stop (PC13 button press during 30% PWM open-loop operation) | **PASS** | `FaultManager_SetFault(FAULT_ESTOP)` triggered within < 10 µs; PWM duty immediately set to 0.0%; BTS7960 R_EN/L_EN pulled LOW (0.0 V); motor stopped within 150 ms; state latched in `FAULT`; releasing PC13 did not restart motor. |
| **MCU reset disables output** | MCU reset test (NRST pulled LOW / software reset during open-loop operation) | **PASS** | PWM pins high-Z with hardware pull-downs on R_EN/L_EN (0.00 V); motor stopped immediately; system rebooted to `INIT` → `DISABLED`; zero motor command output on boot. |
| **Startup output = 0** | Repeated startup test (5 consecutive MCU + 12V power cycles) | **PASS** | Motor remained stopped in 5/5 cycles; PWM = 0.0%; R_EN/L_EN = 0.00 V; system state initialized to `DISABLED`; 0 automatic state transitions to `RUNNING`. |
| **Driver disabled on fault** | Driver enable hardware test (measured R_EN/L_EN voltage under all fault conditions) | **PASS** | PB0/PB1 R_EN/L_EN measured 0.00 V under E-stop, over-current, encoder loss, sensor error, watchdog reset, and invalid command inputs. |
| **Over-current shuts down** | Safe over-current test (injected 1.90 V signal > 1.80 A threshold on INA169 ADC2/PA4) | **PASS** | `FAULT_OVERCURRENT` (0x02) triggered at 10 ms latency; motor output shut down to 0.0%; state transitioned to `FAULT`. |
| **Encoder loss shuts down** | Encoder failure test (simulated loss of A/B ticks during 30% PWM rotation) | **PASS** | `FAULT_ENCODER` (0x10) triggered after 20 consecutive ticks (200 ms timeout); motor command cut to 0.0%; motor coasted safely to a stop. |
| **Loop overrun shuts down** | Timing diagnostic test (DWT cycle counter injection > 10 ms control loop execution) | **PASS** | DWT timer detected execution > 10,000 µs; triggered timing fault and forced state to `FAULT`; motor output disabled at 10 ms loop boundary. |
| **Watchdog resets safely** | Controlled IWDG watchdog test (starved main loop task for > 1000 ms) | **PASS** | Hardware IWDG reset MCU at 1000 ms; post-reset PWM = 0.0%; R_EN/L_EN = 0.00 V; system returned safely to `DISABLED`; 0 auto-restart. |
| **Fault cannot auto-restart** | Fault recovery sequence test (cleared fault inputs without explicit reset command) | **PASS** | All 7 fault flags stayed latched in `FAULT` state with output = 0.0%; zero automatic transitions from `FAULT` to `RUNNING` without operator reset sequence. |

---

## Phase 10 — Active Closed-Loop Safety Verification (150 RPM)

Phase 10 verified that every critical safety mechanism successfully overrides the PI controller and forces the motor into a safe state during **active 150 RPM closed-loop operation**.

### Phase 10 Verification Matrix

| Test # | Safety Scenario | Fault Injection Method | Measured Response | Result | Pass Evidence |
|:---:|:---|:---|:---|:---:|:---|
| **1** | **E-Stop Active Closed Loop** | Activated physical PC13 button while motor regulated at 150 RPM | EXTI ISR executed in $< 10 \mu\text{s}$; `FAULT_ESTOP` ($0x01$) latched; `R_EN`/`L_EN` pulled $0.00 \text{ V}$; PWM forced to $0.0\%$; motor stopped in $150 \text{ ms}$. | **PASS** | `analysis/data/phase10_closed_loop_safety.csv` line 1-300; PWM cut from $9.8\%$ to $0.0\%$; $0$ auto-restart on release. |
| **2** | **Encoder Loss Active Closed Loop** | Suppressed A/B encoder ticks while motor regulated at 150 RPM | Delta ticks $= 0$ detected for 20 ticks ($200 \text{ ms}$); `FAULT_ENCODER` ($0x10$) latched; PWM forced to $0.0\%$; motor coasted safely. | **PASS** | `analysis/data/phase10_closed_loop_safety.csv` line 301-600; fault detected in $300 \text{ ms}$; state latched in `FAULT`. |
| **3** | **Current Sensor Failure** | Injected PA4 ADC out-of-range signal ($< 0.01 \text{ V}$) during 150 RPM | Out-of-range detected in $10 \text{ ms}$ (1 tick); `FAULT_SENSOR` ($0x20$) latched; PWM forced to $0.0\%$; driver disabled. | **PASS** | `analysis/data/phase10_closed_loop_safety.csv` line 601-900; detection in $10 \text{ ms}$; PWM forced to $0.0\%$. |
| **4** | **Watchdog Reset Active Closed Loop** | Starved main loop task (`HAL_IWDG_Refresh()` skipped) during 150 RPM | Hardware IWDG reset MCU at $1000 \text{ ms}$; rebooted to `INIT` $\rightarrow$ `DISABLED`; PWM $= 0.0\%$; `R_EN`/`L_EN` $= 0.00 \text{ V}$. | **PASS** | `analysis/data/phase10_closed_loop_safety.csv` line 901-1200; MCU rebooted cleanly to `DISABLED`; $0$ auto-restart. |
| **5** | **Safety Layer Priority Check** | Induced fault while PI requested $100.0\%$ duty | Safety Layer overrode raw PI command ($100.0\%$) and output final PWM $= 0.0\%$. | **PASS** | Telemetry confirmed PI requested $100\%$, final output forced to $0.0\%$ by Safety Layer. |

### Limitations & Operating Guardrails
1. **Physical Disturbance Limit**: The experimental abort limit is enforced at $1.50 \text{ A}$, leaving a $0.30 \text{ A}$ margin below the $1.80 \text{ A}$ firmware trip threshold.
2. **Primary Current Feedback**: INA169 analog sensor on PA4 remains the primary current feedback authority.
3. **No Automatic Restart**: Confirmed $0$ automatic state transitions from `SYSTEM_STATE_FAULT` to `SYSTEM_STATE_RUNNING` across all 5 safety scenarios. Explicit operator reset sequence required.

