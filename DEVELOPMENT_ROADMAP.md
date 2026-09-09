# Development Roadmap

## Phase 1: Architecture & Planning (Current)
- [x] Establish repository structure.
- [x] Define functional and non-functional requirements.
- [x] Draft software and control architecture.
- [x] Define test plan and hardware criteria.
- **Next Decision Required**: Lock down exact hardware components (STM32 model, Motor, Encoder, Driver).

## Phase 2: Hardware Procurement & BSP Verification
- Procure hardware based on `hardware.md` criteria.
- Configure STM32 clock tree, Timers, ADC, UART, and GPIO via board support package.
- Verify basic hardware communication (Blink LED, transmit UART string).

## Phase 3: Open-Loop & Sensor Validation
- Implement PWM driver. Verify output with an oscilloscope.
- Implement Encoder driver. Verify pulse counting and calculate RPM.
- Implement ADC driver. Verify current measurements.
- Run motor open-loop and capture sensor data to UART.

## Phase 4: Closed-Loop Control Implementation
- Implement discrete-time PI controller with anti-windup.
- Integrate control algorithm into a deterministic timer interrupt.
- Perform step-response testing and tune PID gains.
- Log telemetry data and analyze with Python scripts.

## Phase 5: Safety & Diagnostics
- Implement Fault Manager (overspeed, overcurrent, stall detection).
- Enable hardware Watchdog timer.
- Perform fault injection tests.

## Phase 6: Advanced Goals (Optional)
- Evaluate and implement DMA for telemetry or ADC.
- Migrate to an RTOS (FreeRTOS) for task scheduling.
- Explore advanced control theory.
