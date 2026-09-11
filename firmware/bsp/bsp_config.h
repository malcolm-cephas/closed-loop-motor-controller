/*******************************************************************************
 * @file    bsp_config.h
 * @brief   Board Support Package configuration for NUCLEO-G431RB
 * @note    All pin assignments verified against STM32G431RB datasheet
 *          alternate function tables and NUCLEO-G431RB user manual UM2505.
 *
 * VERIFICATION STATUS:
 *   Pin mappings: VERIFIED BY DATASHEET (STM32G431xB DS, Table 13)
 *   Clock tree:   VERIFIED BY REFERENCE MANUAL (RM0440)
 *   Board config: VERIFIED BY NUCLEO USER MANUAL (UM2505)
 ******************************************************************************/
#ifndef BSP_CONFIG_H
#define BSP_CONFIG_H

/*******************************************************************************
 * SYSTEM CLOCK CONFIGURATION
 * Source: STM32G431RB Reference Manual RM0440, Section 7 (RCC)
 *
 * NUCLEO-G431RB provides 24 MHz HSE from ST-LINK MCO output.
 *
 * PLL Configuration for 170 MHz SYSCLK:
 *   HSE = 24 MHz
 *   PLLM = 6   -> VCO input  = 24/6   = 4 MHz
 *   PLLN = 85  -> VCO output = 4 * 85 = 340 MHz
 *   PLLR = 2   -> SYSCLK     = 340/2  = 170 MHz
 *
 * Bus clocks (with APB prescaler = 1):
 *   HCLK  = 170 MHz (AHB)
 *   PCLK1 = 170 MHz (APB1) -> TIM2-7 clock = 170 MHz
 *   PCLK2 = 170 MHz (APB2) -> TIM1,8 clock = 170 MHz
 *
 * NOTE: If APBx prescaler > 1, timer clocks = 2 * PCLKx (hardware multiplier).
 *       With prescaler = 1, timer clock = PCLKx directly.
 *
 * Flash latency at 170 MHz: 4 wait states (Range 1 Boost mode required).
 ******************************************************************************/
#define BSP_SYSCLK_HZ           170000000UL
#define BSP_HCLK_HZ             170000000UL
#define BSP_PCLK1_HZ            170000000UL
#define BSP_PCLK2_HZ            170000000UL
#define BSP_TIM1_CLK_HZ         170000000UL  /* APB2 timer clock */
#define BSP_TIM2_CLK_HZ         170000000UL  /* APB1 timer clock */

#define BSP_HSE_HZ              24000000UL
#define BSP_PLL_M               6
#define BSP_PLL_N               85
#define BSP_PLL_R               2
#define BSP_FLASH_LATENCY       4  /* Wait states for 170 MHz, Range 1 Boost */

/*******************************************************************************
 * PWM CONFIGURATION — TIM1_CH1 on PA8
 *
 * Verification: PA8 = TIM1_CH1 at AF6 (Datasheet Table 13)
 *
 * TIM1 is on APB2 -> Timer clock = 170 MHz
 *
 * Target PWM frequency: 20 kHz
 *   Prescaler = 0 (no prescaling, full resolution)
 *   ARR = (170,000,000 / 20,000) - 1 = 8499
 *   Resolution: 8500 steps (0.012% per step)
 *
 * Initial duty: 0%
 * Output: DISABLED at startup (MOE bit cleared)
 ******************************************************************************/
#define BSP_PWM_TIM_CLK_HZ      BSP_TIM1_CLK_HZ
#define BSP_PWM_FREQ_HZ         20000
#define BSP_PWM_PRESCALER       0
#define BSP_PWM_ARR             ((BSP_PWM_TIM_CLK_HZ / BSP_PWM_FREQ_HZ) - 1)  /* = 8499 */
#define BSP_PWM_GPIO_PORT       GPIOA
#define BSP_PWM_GPIO_PIN        GPIO_PIN_8
#define BSP_PWM_GPIO_AF         GPIO_AF6_TIM1

/*******************************************************************************
 * ENCODER CONFIGURATION — TIM2 Encoder Mode on PA0/PA1
 *
 * Verification:
 *   PA0 = TIM2_CH1 at AF1 (Datasheet Table 13)
 *   PA1 = TIM2_CH2 at AF1 (Datasheet Table 13)
 *
 * TIM2 is a 32-bit timer on APB1.
 * Counter width: 32 bits (0 to 4,294,967,295)
 * Overflow behavior: Wraps around. Software must handle delta calculation
 *                    using unsigned subtraction for correct signed delta.
 *
 * Encoder counts per output revolution: CONFIGURABLE, NOT HARD-CODED.
 * Must be experimentally verified once hardware arrives.
 ******************************************************************************/
#define BSP_ENC_CHA_PORT        GPIOA
#define BSP_ENC_CHA_PIN         GPIO_PIN_0
#define BSP_ENC_CHA_AF          GPIO_AF1_TIM2
#define BSP_ENC_CHB_PORT        GPIOA
#define BSP_ENC_CHB_PIN         GPIO_PIN_1
#define BSP_ENC_CHB_AF          GPIO_AF1_TIM2
#define BSP_ENC_TIMER_BITS      32

/*******************************************************************************
 * ADC CONFIGURATION — PA4 on ADC2 Channel 17
 *
 * Verification: PA4 = ADC2_IN17 (Datasheet Table 13)
 *
 * IMPORTANT: This is ADC2, NOT ADC1.
 *
 * ADC resolution: 12-bit (4096 counts)
 * Reference voltage: 3.3V (from NUCLEO board VDDA)
 * Sample time: To be configured for adequate settling.
 * Conversion: Software-triggered initially. Timer-triggered later.
 ******************************************************************************/
#define BSP_ADC_CURRENT_PORT    GPIOA
#define BSP_ADC_CURRENT_PIN     GPIO_PIN_4
#define BSP_ADC_INSTANCE        ADC2
#define BSP_ADC_CHANNEL         ADC_CHANNEL_17
#define BSP_ADC_RESOLUTION      12
#define BSP_ADC_VREF            3.3f

/*******************************************************************************
 * UART CONFIGURATION — LPUART1 on PA2/PA3 via ST-LINK VCP
 *
 * Verification: NUCLEO-G431RB UM2505 — PA2/PA3 are connected to ST-LINK VCP
 *               via solder bridges SB17/SB23 (ON by default).
 *
 * CRITICAL NOTE: The default NUCLEO-G431RB routes PA2/PA3 to LPUART1
 *                (NOT USART2). The previous architecture document incorrectly
 *                stated USART2. This has been corrected.
 *
 * Baud rate: 115200
 ******************************************************************************/
#define BSP_UART_TX_PORT        GPIOA
#define BSP_UART_TX_PIN         GPIO_PIN_2
#define BSP_UART_TX_AF          GPIO_AF12_LPUART1
#define BSP_UART_RX_PORT        GPIOA
#define BSP_UART_RX_PIN         GPIO_PIN_3
#define BSP_UART_RX_AF          GPIO_AF12_LPUART1
#define BSP_UART_BAUDRATE       115200

/*******************************************************************************
 * E-STOP GPIO — PC13 (EXTI)
 *
 * Verification: PC13 is the USER BUTTON (B1) on NUCLEO-G431RB (UM2505).
 *               It is active LOW with an external pull-up on the board.
 *
 * For the final system, this pin will be rewired to the physical DPST E-stop.
 * During bring-up, the onboard B1 button can serve as a test E-stop.
 *
 * Trigger: Falling edge (button press = active LOW)
 ******************************************************************************/
#define BSP_ESTOP_PORT          GPIOC
#define BSP_ESTOP_PIN           GPIO_PIN_13
#define BSP_ESTOP_EXTI_LINE     EXTI_LINE_13
#define BSP_ESTOP_IRQn          EXTI15_10_IRQn

/*******************************************************************************
 * DRIVER ENABLE PINS — BTS7960 R_EN / L_EN
 *
 * Selected GPIOs (directly controllable, active HIGH):
 *   PB4 = R_EN (Right Enable)
 *   PB5 = L_EN (Left Enable)
 *
 * These are directly on Morpho connector and do not conflict with
 * any allocated alternate functions.
 ******************************************************************************/
#define BSP_DRV_REN_PORT        GPIOB
#define BSP_DRV_REN_PIN         GPIO_PIN_4
#define BSP_DRV_LEN_PORT        GPIOB
#define BSP_DRV_LEN_PIN         GPIO_PIN_5

/*******************************************************************************
 * BTS7960 PWM INPUTS — RPWM / LPWM
 *
 * For unidirectional forward drive:
 *   RPWM = TIM1_CH1 (PA8) for forward PWM
 *   LPWM = Directly driven LOW (GPIO output) on PB6
 *
 * For bidirectional control (future):
 *   LPWM could be mapped to TIM1_CH2 (PA9, AF6) if needed.
 ******************************************************************************/
#define BSP_DRV_LPWM_PORT      GPIOB
#define BSP_DRV_LPWM_PIN       GPIO_PIN_6

/*******************************************************************************
 * BTS7960 STATUS/FAULT — R_IS / L_IS
 *
 * The BTS7960 module exposes R_IS and L_IS pins which provide an analog
 * current sense output AND fault indication.
 *
 * HOWEVER: These require an external pull-down resistor to convert the
 * internal current source into a readable voltage. The exact behavior and
 * scaling depends on the specific module purchased.
 *
 * STATUS: Driver fault feedback REQUIRES PHYSICAL VERIFICATION.
 *         Do not assume this signal is usable until the module is tested.
 *
 * Tentatively allocated:
 *   PB14 = Driver fault input (digital, EXTI) — if usable after testing.
 ******************************************************************************/
#define BSP_DRV_FAULT_PORT      GPIOB
#define BSP_DRV_FAULT_PIN       GPIO_PIN_14
#define BSP_DRV_FAULT_IRQn      EXTI15_10_IRQn
/* NOTE: Shares IRQ handler with E-STOP (EXTI15_10). Must differentiate
 * in the ISR by checking the pending interrupt flag. */

/*******************************************************************************
 * STATUS LED — PA5 (LD2)
 *
 * Verification: NUCLEO-G431RB UM2505 — Green LED LD2 on PA5, active HIGH.
 ******************************************************************************/
#define BSP_LED_PORT            GPIOA
#define BSP_LED_PIN             GPIO_PIN_5

/*******************************************************************************
 * CONTROL LOOP TIMER — TIM6 (Basic Timer)
 *
 * TIM6 is a basic timer on APB1. Timer clock = 170 MHz.
 *
 * Control loop period: 10 ms (100 Hz)
 *   Prescaler = 169  -> Timer tick = 170 MHz / 170 = 1 MHz (1 us resolution)
 *   ARR = 9999       -> Period = 10000 * 1 us = 10 ms
 ******************************************************************************/
#define BSP_CTRL_TIM_CLK_HZ    BSP_TIM2_CLK_HZ  /* TIM6 is on APB1 */
#define BSP_CTRL_PRESCALER     169
#define BSP_CTRL_ARR           9999
#define BSP_CTRL_IRQn          TIM6_DAC_IRQn

/*******************************************************************************
 * INDEPENDENT WATCHDOG (IWDG)
 *
 * LSI clock: ~32 kHz (varies, not precisely trimmed)
 * Prescaler: 64 -> IWDG clock = 32000/64 = 500 Hz
 * Reload: 500  -> Timeout = 500/500 = 1.0 second
 *
 * The watchdog must be refreshed by the main loop health-check mechanism.
 * If the control loop, state machine, or fault manager fail to signal
 * health within 1 second, the MCU will hard reset.
 ******************************************************************************/
#define BSP_IWDG_PRESCALER      IWDG_PRESCALER_64
#define BSP_IWDG_RELOAD         500

/*******************************************************************************
 * TIMING MEASUREMENT — DWT Cycle Counter
 *
 * The ARM Cortex-M4 Data Watchpoint and Trace (DWT) unit provides a
 * cycle-accurate counter (DWT->CYCCNT) clocked at HCLK (170 MHz).
 * Resolution: ~5.88 ns per tick.
 *
 * Used to measure control-loop execution time and jitter.
 ******************************************************************************/

#endif /* BSP_CONFIG_H */
