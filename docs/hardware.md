# Hardware Interfaces and Selection Criteria

> [!IMPORTANT]
> **Proposed — Not Yet Purchased (Pending Physical Verification)**
> Components are technically evaluated. Pin assignments are VERIFIED BY DATASHEET.

## 1. System Architecture Block Diagram

```text
                ┌───────────────────┐
                │  STM32G431RBT6    │
                │  NUCLEO-G431RB    │
                │                   │
                │  PA8 (TIM1_CH1) ──┼──► RPWM ──┐
                │  PB4 (GPIO) ──────┼──► R_EN ──┤ BTS7960
                │  PB5 (GPIO) ──────┼──► L_EN ──┤ Motor
                │  PB6 (GPIO) ──────┼──► LPWM ──┘ Driver
                │                   │              │
                │  PA0 (TIM2_CH1) ◄─┼── Enc A      │
                │  PA1 (TIM2_CH2) ◄─┼── Enc B    DC Motor
                │                   │           + Encoder
                │  PA4 (ADC2_IN17) ◄┼── Current Sensor
                │                   │
                │  PA2 (LPUART1_TX)─┼──► ST-LINK VCP ──► PC
                │  PA3 (LPUART1_RX)◄┼── ST-LINK VCP ◄── PC
                │                   │
                │  PC13 (EXTI) ◄────┼── E-STOP Button
                │  PA5 (GPIO) ──────┼──► Status LED (LD2)
                └───────────────────┘

    E-STOP (Hardware Path):
       │
       ├──── DPST Pole 1 (NC) → Cuts BTS7960 R_EN/L_EN
       │
       └──── DPST Pole 2 (NO) → Pulls PC13 LOW → EXTI ISR
```

## 2. Verified Peripheral Allocation

| Function | Peripheral | Pin(s) | AF | Verification Source |
|:---|:---|:---|:---|:---|
| PWM Output | TIM1_CH1 | PA8 | AF6 | STM32G431xB Datasheet Table 13 |
| Encoder CH A | TIM2_CH1 | PA0 | AF1 | STM32G431xB Datasheet Table 13 |
| Encoder CH B | TIM2_CH2 | PA1 | AF1 | STM32G431xB Datasheet Table 13 |
| Current ADC | ADC2_IN17 | PA4 | Analog | STM32G431xB Datasheet Table 13 |
| UART TX | LPUART1_TX | PA2 | AF12 | UM2505 + Datasheet |
| UART RX | LPUART1_RX | PA3 | AF12 | UM2505 + Datasheet |
| E-Stop | EXTI | PC13 | — | UM2505 (B1 button) |
| Status LED | GPIO Out | PA5 | — | UM2505 (LD2) |
| Driver R_EN | GPIO Out | PB4 | — | No conflict verified |
| Driver L_EN | GPIO Out | PB5 | — | No conflict verified |
| Driver LPWM | GPIO Out | PB6 | — | No conflict verified |
| Control Timer | TIM6 | — | — | RM0440 |
| Watchdog | IWDG | — | — | RM0440 |

> [!WARNING]
> **UART Correction**: The NUCLEO-G431RB routes PA2/PA3 to **LPUART1** (NOT USART2)
> by default via solder bridges SB17/SB23. The previous architecture document was incorrect.

## 3. Clock Configuration (Verified by Reference Manual RM0440)

| Parameter | Value | Source |
|:---|:---|:---|
| HSE | 24 MHz (ST-LINK MCO) | UM2505 |
| PLL: M / N / R | 6 / 85 / 2 | Calculated |
| SYSCLK | 170 MHz | RM0440 |
| HCLK (AHB) | 170 MHz | Prescaler = 1 |
| PCLK1 (APB1) | 170 MHz | Prescaler = 1 |
| PCLK2 (APB2) | 170 MHz | Prescaler = 1 |
| TIM1 clock | 170 MHz | APB2, prescaler=1 |
| TIM2 clock | 170 MHz | APB1, prescaler=1 |
| Flash latency | 4 WS | Range 1 Boost mode |

## 4. PWM Configuration

| Parameter | Value |
|:---|:---|
| Timer | TIM1 (Advanced Motor Control) |
| Channel | CH1 on PA8 |
| Frequency | 20 kHz |
| Prescaler | 0 (no division) |
| ARR | 8499 |
| Resolution | 8500 steps (0.012% per step) |
| Initial duty | 0% |
| MOE | Disabled at startup |

## 5. Encoder Configuration

| Parameter | Value |
|:---|:---|
| Timer | TIM2 (32-bit) |
| Mode | Hardware Encoder (TIM_ENCODERMODE_TI12 = x4) |
| Counter width | 32-bit (0 to 0xFFFFFFFF) |
| Input filter | 0x0F (digital noise rejection) |
| Pull-ups | Internal pull-up enabled |
| Counts/rev | **PROVISIONAL: 1496** (must verify experimentally) |

## 6. ADC Configuration

| Parameter | Value |
|:---|:---|
| ADC | ADC2 (NOT ADC1) |
| Channel | IN17 on PA4 |
| Resolution | 12-bit (4096 counts) |
| Vref | 3.3V |
| Trigger | Software (initially) |
| Sample time | 47.5 cycles |
| Calibration | HAL auto-calibration at init |

## 7. UART Configuration

| Parameter | Value |
|:---|:---|
| Peripheral | LPUART1 |
| Baud rate | 115200 |
| Routing | PA2/PA3 via ST-LINK VCP (SB17/SB23 ON) |

## 8. Watchdog Configuration

| Parameter | Value |
|:---|:---|
| Type | Independent Watchdog (IWDG) |
| LSI clock | ~32 kHz |
| Prescaler | 64 |
| Reload | 500 |
| Timeout | ~1.0 second |
| Health check | Dual: control loop AND main loop must both execute |

## 9. Safety Mechanisms

- **Fuse**: 3A slow-blow inline (12V rail before driver)
- **E-Stop**: DPST — hardware path cuts R_EN/L_EN; firmware path triggers EXTI
- **Safe Startup**: PWM = 0%, MOE disabled, driver enables LOW
- **Safe Shutdown**: Any fault → FaultManager latches → SafetyLayer forces 0 → MotorDriver disabled

## 10. Physically Verified Hardware Characteristics

| Item | Measured Value | Verification Method |
|:---|:---|:---|
| Encoder PPR | **1496 counts/output rev** | 10 manual forward/reverse shaft revolutions |
| Encoder pull-ups | **Internal pull-ups sufficient** | Verified crisp square wave via oscilloscope |
| INA169 V/A scaling | **1.0 V/A** (not 0.5 V/A) | Tested with 0.5A and 1.0A resistive loads |
| INA169 zero offset | **0.02 V (approx 24 counts)** | Measured at zero current |
| BTS7960 IS pins | **Unusable for precise analog fault detection** | Measured during sweep; noisy and non-linear. Software overcurrent is preferred. |
| Motor stall current | **~1.8A at 12V** | Bench power supply measurement. |
| Motor dead-zone | **~10% PWM duty** | Open-loop sweep: motor begins moving reliably at 15%. |
| Steady-state speed | **~248 RPM at 100% duty** | Open-loop sweep at 12V supply. |
