# Development Roadmap

## Phase 1: Architecture & Planning ✅
- [x] Establish repository structure.
- [x] Define functional and non-functional requirements.
- [x] Draft software and control architecture.
- [x] Define test plan and hardware criteria.
- [x] Propose and review hardware components.

## Phase 2: Hardware-Independent Firmware & Simulation ✅
- [x] Implement system state machine.
- [x] Implement PI controller (hardware-independent).
- [x] Implement speed estimator (hardware-independent).
- [x] Implement current monitor (hardware-independent).
- [x] Implement fault manager and safety layer.
- [x] Create C unit test framework.
- [x] Create Python motor simulation.
- [x] Create performance metrics analysis tools.
- [x] Perform PI tuning parameter sweep.

## Phase 3: STM32 Hardware Integration (Current)
- [x] Verify pin mappings against STM32G431RB datasheet.
- [x] Create BSP layer (bsp_config.h, bsp.h, bsp.c).
- [x] Configure system clock (170 MHz via PLL).
- [x] Configure PWM (TIM1_CH1, 20 kHz).
- [x] Configure Encoder (TIM2 hardware encoder mode).
- [x] Configure ADC (ADC2_IN17, 12-bit).
- [x] Configure UART (LPUART1, 115200 baud).
- [x] Configure E-Stop (PC13 EXTI).
- [x] Configure Watchdog (IWDG, 1s timeout).
- [x] Implement control loop timer (TIM6, 100 Hz).
- [x] Implement timing diagnostics (DWT cycle counter).
- [x] Create driver abstraction layer.
- [x] Create main.c with bring-up firmware.
- [x] Update documentation.
- [ ] **PENDING**: Build with STM32CubeIDE/CMake toolchain.
- [ ] **PENDING**: Flash and execute hardware bring-up checklist.

## Phase 4: Motor Operation & Closed-Loop Control
- [ ] Complete hardware bring-up checklist (all 11 steps).
- [ ] Experimentally verify encoder PPR.
- [ ] Calibrate current sensor.
- [ ] Enable motor output.
- [ ] Run open-loop motor test.
- [ ] Enable closed-loop PI control.
- [ ] Perform step-response testing with real hardware.
- [ ] Retune PI gains based on real plant response.
- [ ] Log and analyze real telemetry data.

## Phase 5: Safety & Fault Validation
- [ ] Perform all fault injection tests.
- [ ] Validate overcurrent protection.
- [ ] Validate stall detection.
- [ ] Validate E-stop hardware path.
- [ ] Validate watchdog recovery.

## Phase 6: Advanced Goals (Optional)
- [ ] Evaluate DMA for telemetry or ADC.
- [ ] Migrate to FreeRTOS for task scheduling.
- [ ] Explore advanced control algorithms.
- [ ] Investigate CAN bus communication.
