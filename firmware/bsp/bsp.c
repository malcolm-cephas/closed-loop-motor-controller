/*******************************************************************************
 * @file    bsp.c
 * @brief   Board Support Package implementation for NUCLEO-G431RB
 *
 * Contains all STM32 HAL peripheral initialization and hardware access.
 * This file is the boundary between portable firmware and MCU-specific code.
 *
 * TARGET: STM32G431RBT6 on NUCLEO-G431RB
 * HAL:    STM32G4 HAL
 ******************************************************************************/

#include "bsp.h"
#include "bsp_config.h"
#include "stm32g4xx_hal.h"

/* ---- HAL Handles ---- */
static TIM_HandleTypeDef htim1;   /* PWM */
static TIM_HandleTypeDef htim2;   /* Encoder */
static TIM_HandleTypeDef htim6;   /* Control loop */
static ADC_HandleTypeDef hadc2;   /* Current sensor */
static UART_HandleTypeDef hlpuart1; /* Telemetry */
static IWDG_HandleTypeDef hiwdg;  /* Watchdog */

/*******************************************************************************
 * SYSTEM CLOCK — 170 MHz from HSE via PLL
 ******************************************************************************/
void BSP_SystemClock_Config(void) {
    RCC_OscInitTypeDef rcc_osc = {0};
    RCC_ClkInitTypeDef rcc_clk = {0};

    /* Enable Range 1 Boost mode for 170 MHz operation */
    HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1_BOOST);

    /* HSE from ST-LINK MCO = 24 MHz */
    rcc_osc.OscillatorType = RCC_OSCILLATORTYPE_HSE | RCC_OSCILLATORTYPE_LSI;
    rcc_osc.HSEState       = RCC_HSE_ON;
    rcc_osc.LSIState       = RCC_LSI_ON;  /* Required for IWDG */
    rcc_osc.PLL.PLLState   = RCC_PLL_ON;
    rcc_osc.PLL.PLLSource  = RCC_PLLSOURCE_HSE;
    rcc_osc.PLL.PLLM       = RCC_PLLM_DIV6;
    rcc_osc.PLL.PLLN       = BSP_PLL_N;    /* 85 */
    rcc_osc.PLL.PLLP       = RCC_PLLP_DIV2;
    rcc_osc.PLL.PLLQ       = RCC_PLLQ_DIV2;
    rcc_osc.PLL.PLLR       = RCC_PLLR_DIV2;
    HAL_RCC_OscConfig(&rcc_osc);

    /* Select PLL as system clock, configure bus prescalers */
    rcc_clk.ClockType      = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                             RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    rcc_clk.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
    rcc_clk.AHBCLKDivider  = RCC_SYSCLK_DIV1;
    rcc_clk.APB1CLKDivider = RCC_HCLK_DIV1;
    rcc_clk.APB2CLKDivider = RCC_HCLK_DIV1;
    HAL_RCC_ClockConfig(&rcc_clk, FLASH_LATENCY_4);
}

/*******************************************************************************
 * GPIO CLOCK ENABLE — Must precede all GPIO init
 ******************************************************************************/
static void BSP_GPIO_ClockEnable(void) {
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
}

/*******************************************************************************
 * PWM — TIM1_CH1 on PA8, 20 kHz
 ******************************************************************************/
void BSP_PWM_Init(void) {
    __HAL_RCC_TIM1_CLK_ENABLE();

    /* Configure PA8 as TIM1_CH1 AF6 */
    GPIO_InitTypeDef gpio = {0};
    gpio.Pin       = BSP_PWM_GPIO_PIN;
    gpio.Mode      = GPIO_MODE_AF_PP;
    gpio.Pull      = GPIO_NOPULL;
    gpio.Speed     = GPIO_SPEED_FREQ_HIGH;
    gpio.Alternate = BSP_PWM_GPIO_AF;
    HAL_GPIO_Init(BSP_PWM_GPIO_PORT, &gpio);

    /* TIM1 base: 170 MHz / (0+1) = 170 MHz tick, ARR = 8499 -> 20 kHz */
    htim1.Instance               = TIM1;
    htim1.Init.Prescaler         = BSP_PWM_PRESCALER;
    htim1.Init.CounterMode       = TIM_COUNTERMODE_UP;
    htim1.Init.Period            = BSP_PWM_ARR;
    htim1.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
    htim1.Init.RepetitionCounter = 0;
    htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    HAL_TIM_PWM_Init(&htim1);

    TIM_OC_InitTypeDef oc = {0};
    oc.OCMode     = TIM_OCMODE_PWM1;
    oc.Pulse      = 0;  /* 0% duty at startup */
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    oc.OCFastMode = TIM_OCFAST_DISABLE;
    HAL_TIM_PWM_ConfigChannel(&htim1, &oc, TIM_CHANNEL_1);

    /* Do NOT start PWM yet. MOE remains cleared until BSP_PWM_Enable(). */
}

void BSP_PWM_Enable(void) {
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
    /* For advanced timers, MOE must be set explicitly */
    __HAL_TIM_MOE_ENABLE(&htim1);
}

void BSP_PWM_Disable(void) {
    __HAL_TIM_MOE_DISABLE(&htim1);
    HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
}

void BSP_PWM_SetDuty(float duty_percent) {
    if (duty_percent < 0.0f) duty_percent = 0.0f;
    if (duty_percent > 100.0f) duty_percent = 100.0f;
    uint32_t compare = (uint32_t)((duty_percent / 100.0f) * (float)(BSP_PWM_ARR + 1));
    __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, compare);
}

/*******************************************************************************
 * MOTOR DRIVER ENABLE — BTS7960 R_EN/L_EN on PB4/PB5
 ******************************************************************************/
void BSP_DriverEnable_Init(void) {
    GPIO_InitTypeDef gpio = {0};
    gpio.Mode  = GPIO_MODE_OUTPUT_PP;
    gpio.Pull  = GPIO_PULLDOWN;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;

    gpio.Pin = BSP_DRV_REN_PIN;
    HAL_GPIO_Init(BSP_DRV_REN_PORT, &gpio);

    gpio.Pin = BSP_DRV_LEN_PIN;
    HAL_GPIO_Init(BSP_DRV_LEN_PORT, &gpio);

    /* BTS7960 LPWM driven LOW for unidirectional forward drive */
    gpio.Pin = BSP_DRV_LPWM_PIN;
    HAL_GPIO_Init(BSP_DRV_LPWM_PORT, &gpio);

    /* All outputs LOW at startup — driver disabled */
    HAL_GPIO_WritePin(BSP_DRV_REN_PORT, BSP_DRV_REN_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(BSP_DRV_LEN_PORT, BSP_DRV_LEN_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(BSP_DRV_LPWM_PORT, BSP_DRV_LPWM_PIN, GPIO_PIN_RESET);
}

void BSP_DriverEnable_Set(bool enabled) {
    GPIO_PinState state = enabled ? GPIO_PIN_SET : GPIO_PIN_RESET;
    HAL_GPIO_WritePin(BSP_DRV_REN_PORT, BSP_DRV_REN_PIN, state);
    HAL_GPIO_WritePin(BSP_DRV_LEN_PORT, BSP_DRV_LEN_PIN, state);
}

/*******************************************************************************
 * ENCODER — TIM2 Hardware Encoder Mode on PA0/PA1
 * TIM2 is 32-bit. Counter wraps at 0xFFFFFFFF.
 * Signed delta is obtained by unsigned subtraction of current - previous.
 ******************************************************************************/
void BSP_Encoder_Init(void) {
    __HAL_RCC_TIM2_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};
    gpio.Mode      = GPIO_MODE_AF_PP;
    gpio.Pull      = GPIO_PULLUP;
    gpio.Speed     = GPIO_SPEED_FREQ_HIGH;

    gpio.Pin       = BSP_ENC_CHA_PIN;
    gpio.Alternate = BSP_ENC_CHA_AF;
    HAL_GPIO_Init(BSP_ENC_CHA_PORT, &gpio);

    gpio.Pin       = BSP_ENC_CHB_PIN;
    gpio.Alternate = BSP_ENC_CHB_AF;
    HAL_GPIO_Init(BSP_ENC_CHB_PORT, &gpio);

    TIM_Encoder_InitTypeDef enc = {0};
    htim2.Instance           = TIM2;
    htim2.Init.Prescaler     = 0;
    htim2.Init.CounterMode   = TIM_COUNTERMODE_UP;
    htim2.Init.Period        = 0xFFFFFFFF;  /* 32-bit full range */
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;

    enc.EncoderMode  = TIM_ENCODERMODE_TI12; /* x4 decoding: count both edges of both channels */
    enc.IC1Polarity  = TIM_ICPOLARITY_RISING;
    enc.IC1Selection = TIM_ICSELECTION_DIRECTTI;
    enc.IC1Prescaler = TIM_ICPSC_DIV1;
    enc.IC1Filter    = 0x0F; /* Digital filter for noise rejection */
    enc.IC2Polarity  = TIM_ICPOLARITY_RISING;
    enc.IC2Selection = TIM_ICSELECTION_DIRECTTI;
    enc.IC2Prescaler = TIM_ICPSC_DIV1;
    enc.IC2Filter    = 0x0F;

    HAL_TIM_Encoder_Init(&htim2, &enc);
    HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
}

int32_t BSP_Encoder_GetCount(void) {
    return (int32_t)__HAL_TIM_GET_COUNTER(&htim2);
}

void BSP_Encoder_Reset(void) {
    __HAL_TIM_SET_COUNTER(&htim2, 0);
}

/*******************************************************************************
 * ADC — ADC2 Channel 17 on PA4, 12-bit, software triggered
 ******************************************************************************/
void BSP_ADC_Init(void) {
    __HAL_RCC_ADC12_CLK_ENABLE();

    /* Configure PA4 as analog */
    GPIO_InitTypeDef gpio = {0};
    gpio.Pin  = BSP_ADC_CURRENT_PIN;
    gpio.Mode = GPIO_MODE_ANALOG;
    gpio.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(BSP_ADC_CURRENT_PORT, &gpio);

    hadc2.Instance                   = ADC2;
    hadc2.Init.ClockPrescaler        = ADC_CLOCK_ASYNC_DIV4;
    hadc2.Init.Resolution            = ADC_RESOLUTION_12B;
    hadc2.Init.DataAlign             = ADC_DATAALIGN_RIGHT;
    hadc2.Init.ScanConvMode          = ADC_SCAN_DISABLE;
    hadc2.Init.EOCSelection          = ADC_EOC_SINGLE_CONV;
    hadc2.Init.LowPowerAutoWait      = DISABLE;
    hadc2.Init.ContinuousConvMode    = DISABLE;
    hadc2.Init.NbrOfConversion       = 1;
    hadc2.Init.DiscontinuousConvMode = DISABLE;
    hadc2.Init.ExternalTrigConv      = ADC_SOFTWARE_START;
    hadc2.Init.ExternalTrigConvEdge  = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc2.Init.Overrun               = ADC_OVR_DATA_OVERWRITTEN;
    hadc2.Init.OversamplingMode      = DISABLE;
    HAL_ADC_Init(&hadc2);

    /* Configure channel */
    ADC_ChannelConfTypeDef ch = {0};
    ch.Channel      = BSP_ADC_CHANNEL;
    ch.Rank         = ADC_REGULAR_RANK_1;
    ch.SamplingTime = ADC_SAMPLETIME_47CYCLES_5;
    ch.SingleDiff   = ADC_SINGLE_ENDED;
    ch.OffsetNumber = ADC_OFFSET_NONE;
    HAL_ADC_ConfigChannel(&hadc2, &ch);

    /* Run ADC calibration */
    HAL_ADCEx_Calibration_Start(&hadc2, ADC_SINGLE_ENDED);
}

uint32_t BSP_ADC_ReadRaw(void) {
    HAL_ADC_Start(&hadc2);
    HAL_ADC_PollForConversion(&hadc2, 10);
    uint32_t val = HAL_ADC_GetValue(&hadc2);
    HAL_ADC_Stop(&hadc2);
    return val;
}

/*******************************************************************************
 * UART — LPUART1 on PA2/PA3 via ST-LINK VCP, 115200 baud
 ******************************************************************************/
void BSP_UART_Init(void) {
    __HAL_RCC_LPUART1_CLK_ENABLE();

    GPIO_InitTypeDef gpio = {0};
    gpio.Mode      = GPIO_MODE_AF_PP;
    gpio.Pull      = GPIO_PULLUP;
    gpio.Speed     = GPIO_SPEED_FREQ_HIGH;

    gpio.Pin       = BSP_UART_TX_PIN;
    gpio.Alternate = BSP_UART_TX_AF;
    HAL_GPIO_Init(BSP_UART_TX_PORT, &gpio);

    gpio.Pin       = BSP_UART_RX_PIN;
    gpio.Alternate = BSP_UART_RX_AF;
    HAL_GPIO_Init(BSP_UART_RX_PORT, &gpio);

    hlpuart1.Instance            = LPUART1;
    hlpuart1.Init.BaudRate       = BSP_UART_BAUDRATE;
    hlpuart1.Init.WordLength     = UART_WORDLENGTH_8B;
    hlpuart1.Init.StopBits       = UART_STOPBITS_1;
    hlpuart1.Init.Parity         = UART_PARITY_NONE;
    hlpuart1.Init.Mode           = UART_MODE_TX_RX;
    hlpuart1.Init.HwFlowCtl      = UART_HWCONTROL_NONE;
    hlpuart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
    hlpuart1.Init.ClockPrescaler = UART_PRESCALER_DIV1;
    HAL_UART_Init(&hlpuart1);
}

void BSP_UART_Transmit(const uint8_t* data, uint16_t length) {
    HAL_UART_Transmit(&hlpuart1, data, length, 50);
}

bool BSP_UART_TransmitReady(void) {
    return (hlpuart1.gState == HAL_UART_STATE_READY);
}

/*******************************************************************************
 * E-STOP — PC13 (B1 Button), Falling Edge EXTI
 ******************************************************************************/
void BSP_EStop_Init(void) {
    GPIO_InitTypeDef gpio = {0};
    gpio.Pin  = BSP_ESTOP_PIN;
    gpio.Mode = GPIO_MODE_IT_FALLING;
    gpio.Pull = GPIO_NOPULL; /* External pull-up on NUCLEO board */
    HAL_GPIO_Init(BSP_ESTOP_PORT, &gpio);

    HAL_NVIC_SetPriority(BSP_ESTOP_IRQn, 0, 0); /* Highest priority */
    HAL_NVIC_EnableIRQ(BSP_ESTOP_IRQn);
}

bool BSP_EStop_IsPressed(void) {
    return (HAL_GPIO_ReadPin(BSP_ESTOP_PORT, BSP_ESTOP_PIN) == GPIO_PIN_RESET);
}

/*******************************************************************************
 * STATUS LED — PA5 (LD2)
 ******************************************************************************/
void BSP_LED_Init(void) {
    GPIO_InitTypeDef gpio = {0};
    gpio.Pin   = BSP_LED_PIN;
    gpio.Mode  = GPIO_MODE_OUTPUT_PP;
    gpio.Pull  = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(BSP_LED_PORT, &gpio);
}

void BSP_LED_Toggle(void) {
    HAL_GPIO_TogglePin(BSP_LED_PORT, BSP_LED_PIN);
}

void BSP_LED_Set(bool on) {
    HAL_GPIO_WritePin(BSP_LED_PORT, BSP_LED_PIN, on ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/*******************************************************************************
 * CONTROL LOOP TIMER — TIM6 at 100 Hz (10 ms period)
 ******************************************************************************/
void BSP_ControlTimer_Init(void) {
    __HAL_RCC_TIM6_CLK_ENABLE();

    htim6.Instance               = TIM6;
    htim6.Init.Prescaler         = BSP_CTRL_PRESCALER;   /* 169 -> 1 MHz tick */
    htim6.Init.CounterMode       = TIM_COUNTERMODE_UP;
    htim6.Init.Period            = BSP_CTRL_ARR;          /* 9999 -> 10 ms */
    htim6.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    HAL_TIM_Base_Init(&htim6);

    HAL_NVIC_SetPriority(BSP_CTRL_IRQn, 1, 0); /* High priority, below E-stop */
    HAL_NVIC_EnableIRQ(BSP_CTRL_IRQn);

    HAL_TIM_Base_Start_IT(&htim6);
}

/*******************************************************************************
 * WATCHDOG — IWDG, ~1 second timeout
 ******************************************************************************/
void BSP_Watchdog_Init(void) {
    hiwdg.Instance       = IWDG;
    hiwdg.Init.Prescaler = BSP_IWDG_PRESCALER;
    hiwdg.Init.Reload    = BSP_IWDG_RELOAD;
    hiwdg.Init.Window    = IWDG_WINDOW_DISABLE;
    HAL_IWDG_Init(&hiwdg);
}

void BSP_Watchdog_Refresh(void) {
    HAL_IWDG_Refresh(&hiwdg);
}

/*******************************************************************************
 * DWT CYCLE COUNTER — For timing measurement
 ******************************************************************************/
void BSP_CycleCounter_Init(void) {
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

uint32_t BSP_CycleCounter_Get(void) {
    return DWT->CYCCNT;
}

/*******************************************************************************
 * MASTER INIT
 ******************************************************************************/
void BSP_Init(void) {
    HAL_Init();
    BSP_SystemClock_Config();
    BSP_GPIO_ClockEnable();
    BSP_LED_Init();
    BSP_EStop_Init();
    BSP_DriverEnable_Init();
    BSP_PWM_Init();
    BSP_Encoder_Init();
    BSP_ADC_Init();
    BSP_UART_Init();
    BSP_ControlTimer_Init();
    BSP_CycleCounter_Init();
    /* Watchdog initialized separately after system health is confirmed */
}
