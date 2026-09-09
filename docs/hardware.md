# Hardware Interfaces and Selection Criteria

> [!IMPORTANT]
> **Proposed — Not Yet Purchased (Pending Physical Verification)**
> The components listed below are technically evaluated but require experimental verification upon arrival. Do not rely on vendor marketplace listings as authoritative datasheets.

## 1. System Architecture Block Diagram

```text
                ┌──────────────┐
                │    STM32     │
                │  G431RB      │
                └──────┬───────┘
                       │
         ┌─────────────┼──────────────┐
         ↓             ↓              ↓
      Encoder         ADC           UART
         │             │              │
         │          Current         PC
         │          Sensor
         ↓
   Speed Measurement
         ↓
    PI Controller
         ↓
        PWM
         ↓
   Motor Driver
         ↓
      DC Motor
         │
         └──────────── Encoder

    E-STOP
       │
       ├──── Hardware motor disable (Driver EN pins)
       │
       └──── STM32 fault input (EXTI)
```

## 2. Microcontroller (STM32)
- **Proposed Part**: **NUCLEO-G431RB**
- **Key Specifications**: 170 MHz Cortex-M4, advanced motor-control timers, 12-bit ADCs, internal Op-Amps.
- **Peripheral Allocation (Proposed)**:
  - **PWM**: TIM1 (Advanced Motor Control Timer) on PA8 (CH1) and PA9 (CH2)
  - **Encoder**: TIM2 (Encoder Mode/Input Capture) on PA0 (CH1), PA1 (CH2)
  - **Current ADC**: ADC1 on PA4 (Avoids PA2/PA3 USART2 conflict)
  - **UART**: USART2 on PA2 (TX), PA3 (RX) - linked to ST-LINK USB
  - **E-Stop Input**: PC13 (or external GPIO with EXTI)
  - **Fault Input**: PB14 (EXTI from motor driver if applicable)
  - **Status LED**: PA5 (Onboard LED)
- **Selection Rationale**: Industry standard for modern ST motor control. Powerful timers and ADCs prevent hardware bottlenecks.

## 3. DC Motor & Encoder
- **Proposed Part**: **JGA25-370 12V DC Gear Motor with Hall-Effect Encoder**
- **Key Specifications**: ~300 RPM output, 12V, ~2A stall.
- **Encoder Requirements & Verification**:
  - **Type**: Magnetic incremental quadrature.
  - **Resolution**: *Vendor listings often claim 11 PPR at the motor shaft.* With a 34:1 gearbox, this is 374 PPR. In 4X decoding, 1496 counts/rev.
  - **Measurable RPM**: At a 100Hz control loop, 1 encoder count per 10ms equates to a minimum measurable speed resolution of ~4 RPM.
  - **Electrical**: Usually 3.3V/5V compatible. 
- **Selection Rationale**: Safe, affordable, perfect for benchtop PID experiments.

## 4. Motor Driver
- **Proposed Part**: **BTS7960 43A Half-Bridge Module**
- **Key Specifications**: 43A peak, 5.5V-27V, 3.3V/5V logic compatible.
- **Selection Rationale**: 43A is massive overkill for a 2A motor, but it is indestructible for student experiments, handles high-frequency PWM, and has excellent thermal mass.
- **Logic Requirements**: Requires R_EN, L_EN (Enable pins), and R_PWM, L_PWM. 
- **Alternatives Evaluated**: 
  - *DRV8871 (3.6A)*: Technically a more modern, correctly-sized driver with internal current limiting. However, less ubiquitous in local Indian stores.
  - *TB6612FNG (1.2A)*: Insufficient current margin for a 2A stall.
- We will proceed with the BTS7960 for availability and extreme safety margins.

## 5. Current Sensor
- **Proposed Part**: **INA169 Analog Current Sensor Breakout**
- **Key Specifications**: High-side analog current monitor, unipolar output.
- **Selection Rationale**: Superior to the ACS712 for this application. The ACS712 is noisy and operates on 5V (resulting in a 2.5V zero-offset that wastes ADC dynamic range). The INA169 outputs a ground-referenced analog voltage directly proportional to the current, easily and safely read by the STM32's 3.3V ADC with high bandwidth and low noise.
- **Alternative**: ACS712 5A module (acceptable, but requires low-pass filtering and careful 3.3V limit verification).

## 6. Power System & Safety
- **Power Supply**: 12V 5A DC SMPS.
- **Logic Power**: STM32 powered via USB (5V -> internal 3.3V LDO).
- **Fuse**: **3A Slow-Blow** automotive blade fuse. Placed in series with the positive 12V line *before* the motor driver to protect against dead shorts.
- **Bulk Capacitance**: 470uF to 1000uF electrolytic capacitor across the motor driver 12V input to absorb inductive flyback.
- **Hardware E-Stop Architecture**: 
  - A physical DPST (Double Pole Single Throw) latching mushroom button.
  - **Pole 1 (NC)**: Placed in series with the BTS7960's logic enable lines (R_EN, L_EN). Pressing it instantly cuts hardware enable, safely coasting the motor regardless of firmware state.
  - **Pole 2 (NO)**: Pulls an STM32 GPIO high to trigger a firmware fault state interrupt.

## 7. Signal Integrity & Wiring
- **Encoder**: Twisted pair for A/B signals. Keep routed away from motor power wires.
- **PWM**: Keep logic wires short to prevent ringing.
- **Analog Sensor**: Route away from switching nodes. Use a small hardware RC low-pass filter (e.g., 1kΩ, 10nF) at the STM32 ADC pin to reject high-frequency PWM noise.
- **Grounding**: **Star Grounding** is mandatory. The STM32 GND, Current Sensor GND, and Motor Driver logic GND must tie to a single common point at the Driver's ground terminal to prevent motor return currents from shifting the MCU's ground reference.

## 8. Final Proposed BOM
| Component | Exact Part/Model | Qty | Purpose | Key Spec | Approx Price (INR) | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **MCU** | NUCLEO-G431RB | 1 | Main Controller | 170MHz, Adv Timers | ~₹2000 | Industry standard for motor control |
| **Motor** | JGA25-370 w/ Encoder | 1 | Actuator/Plant | 12V, ~300RPM | ~₹600 | Affordable, safe benchtop profile |
| **Driver** | BTS7960 Module | 1 | Power Stage | 43A, 3.3V logic | ~₹350 | Indestructible safety margin |
| **Current Sensor**| INA169 Breakout | 1 | Telemetry/Safety | Analog High-Side | ~₹250 | Ground-referenced, low noise |
| **Power Supply** | Generic 12V 5A SMPS| 1 | Motor Power | 60W | ~₹400 | Sufficient overhead |
| **E-Stop** | Latching Mushroom | 1 | Hardware Safety | DPST (NO/NC) | ~₹150 | Hardware-level disable |
| **Fuse** | 3A Slow-Blow | 1 | Overcurrent Protection | 3A | ~₹20 | Protects against dead shorts |

## 9. Hardware Decisions Pending Physical Verification
*Do not write firmware based on assumptions. Verify these experimentally once hardware arrives:*
1. **Encoder Resolution**: Must manually rotate the shaft 10 times and count edges in firmware to determine the exact `Counts/Revolution`.
2. **Encoder Electricals**: Must verify if the encoder requires external pull-up resistors (open-drain) or if STM32 internal pull-ups suffice.
3. **Current Sensor Scaling**: Must verify the exact $V_{out} / Amp$ scaling of the INA169 breakout board, as the onboard sense resistor value varies by generic vendor.
4. **Motor Polarity**: Verify PWM duty-cycle direction matches encoder count direction (positive duty = positive count).
