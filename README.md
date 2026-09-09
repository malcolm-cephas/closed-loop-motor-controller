# Digital Closed-Loop DC Motor Speed Control System

## Project Overview
An advanced, real-time embedded system designed to control the speed of a DC motor using feedback from a quadrature encoder. The system maintains a commanded RPM despite load disturbances and includes real-time telemetry, current monitoring, fault detection, and hardware safety mechanisms.

## Motivation
This project is engineered as a core embedded-systems portfolio piece. It moves beyond basic Arduino hobby projects by enforcing deterministic execution, modular C architecture, explicit hardware safety mechanisms, and rigorous data analysis.

## System Architecture
* [Software Architecture](docs/architecture.md)
* [Control System Design](docs/control_design.md)
* [Hardware Interfaces](docs/hardware.md)
* [Requirements](docs/requirements.md)
* [Test Plan](docs/test_plan.md)

## Control Algorithm
The system utilizes a discrete-time Proportional-Integral (PI) control algorithm executing at a strictly deterministic frequency inside a hardware timer interrupt. It features integral anti-windup, output saturation, and safe initialization protocols.

## Hardware (Proposed)
- **MCU**: STM32 Series
- **Actuation**: DC Motor + Motor Driver (H-Bridge)
- **Sensors**: Quadrature Encoder, ADC-based Current Sensor
- **Communication**: UART to PC for telemetry

## Results & Analysis
*(To be populated after implementation and testing. Will include plots for step response, load disturbance, and telemetry.)*

## Limitations & Future Improvements
*(To be updated as development progresses. Advanced goals include DMA, FreeRTOS integration, and advanced control algorithms.)*
