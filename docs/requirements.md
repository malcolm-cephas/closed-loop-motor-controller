# Requirements Document
## 1. Functional Requirements
- **FR1**: The system shall control the speed of a DC motor using a closed-loop control algorithm (PI/PID).
- **FR2**: The system shall measure the motor speed using a quadrature encoder.
- **FR3**: The system shall allow the target RPM to be adjusted dynamically.
- **FR4**: The system shall output a PWM signal to drive the motor via a motor driver.
- **FR5**: The system shall measure motor current via an ADC channel.
- **FR6**: The system shall provide real-time telemetry over a UART connection.
- **FR7**: The system shall detect fault conditions (overcurrent, overspeed, stall, sensor loss, E-stop) and execute a safe shutdown.

## 2. Non-Functional Requirements
- **NFR1**: The control loop shall execute at a deterministic, fixed period using a hardware timer.
- **NFR2**: The firmware shall be modular, written in embedded C, avoiding bloated abstractions.
- **NFR3**: The system shall include an independent hardware watchdog timer.

## 3. Timing Requirements (Provisional)
- **TR1**: Control loop period: 10 ms (100 Hz). *[Assumption: Needs verification based on motor time constant]*
- **TR2**: Maximum acceptable timing jitter: < 5% of control loop period (0.5 ms).
- **TR3**: Telemetry update rate: 10-50 Hz depending on baud rate capabilities.
- **TR4**: Fault response time: < 1 ms from detection to PWM shutdown.

## 4. Safety Requirements
- **SR1**: Hardware and firmware shall support overcurrent protection.
- **SR2**: The system shall feature an overspeed protection threshold.
- **SR3**: Motor stall detection shall trigger a fault and cut power to prevent thermal runaway.
- **SR4**: Safe startup: the system shall start in a zero-PWM state until explicitly enabled.
- **SR5**: Safe shutdown: on any detected fault or watchdog reset, PWM shall immediately be driven to a safe state.
- **SR6**: Hardware E-Stop: A physical DPST E-stop button must cut driver enable signals via hardware, completely bypassing firmware, while simultaneously signaling the MCU.

## 5. Measurable Performance Targets (Provisional)
- **PT1**: Target RPM range: 100 to 3000 RPM. *[Assumption: Depends on selected motor]*
- **PT2**: Acceptable steady-state error: < 2% of target RPM.
- **PT3**: Acceptable overshoot: < 5% for step responses without load.
- **PT4**: Settling time: < 500 ms for a 1000 RPM step input.

## 6. Assumptions
### 6.1 Hardware Assumptions
- Encoder PPR and output type (open-drain vs push-pull) will be experimentally verified before finalizing speed estimation math.
- The INA169 current sensor scaling factor will be verified experimentally.
- Motor specifications (stall current, exact no-load RPM) are approximations based on marketplace listings and require verification.

### 6.2 Software Assumptions
- A bare-metal architecture (interrupt-driven) is sufficient for initial implementation before evaluating RTOS integration.
- Floating-point or scaled fixed-point math will be used for the control loop without violating timing constraints.

## 7. Test Requirements
- The system must pass unit tests for control math, fault logic, and state transitions.
- The system must pass hardware-in-the-loop tests measuring step response, disturbance rejection, and fault induction.
