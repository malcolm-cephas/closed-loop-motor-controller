# Software Architecture

## 1. Firmware Layer Diagram

```text
┌─────────────────────────────────────────────────┐
│                  main.c                         │
│         (Startup, main loop, ISR glue)          │
├─────────────────────────────────────────────────┤
│               Application Layer                 │
│   system_state    control_loop                  │
├──────────────────┬──────────────────────────────┤
│   Control Layer  │   Safety Layer               │
│   pi_controller  │   fault_manager              │
│   speed_estimator│   safety_layer               │
├──────────────────┼──────────────────────────────┤
│   Sensors        │   Communication              │
│   current_monitor│   telemetry_format            │
│                  │   uart_telemetry              │
│                  │   command_parser              │
├──────────────────┴──────────────────────────────┤
│               Drivers Layer                     │
│   motor_driver     encoder_driver               │
├─────────────────────────────────────────────────┤
│          BSP (Board Support Package)            │
│   bsp.h / bsp.c / bsp_config.h                 │
│   (ONLY layer that calls STM32 HAL functions)   │
├─────────────────────────────────────────────────┤
│           STM32G4 HAL / CMSIS                   │
└─────────────────────────────────────────────────┘
```

## 2. System State Machine

```text
  ┌──────┐
  │ INIT │──────────────────────────┐
  └──┬───┘                          │
     │ (boot complete)              │
     ▼                              │
  ┌──────────┐                      │ ANY STATE
  │ DISABLED │◄────────────┐        │     │
  └──┬───────┘             │        │     ▼
     │ (safety OK,         │     ┌──────┐
     │  no faults,         │     │FAULT │ (PWM forced to 0,
     │  E-stop released)   │     └──┬───┘  driver disabled)
     ▼                     │        │
  ┌──────┐                 │        │ (clear faults + user request)
  │ARMED │                 │        │
  └──┬───┘                 │        ▼
     │ (explicit START)    └────────┘
     ▼
  ┌────────┐
  │RUNNING │ (PI active, motor output permitted)
  └────────┘
```

### Transition Rules:
- `INIT → DISABLED`: Automatic after boot initialization completes.
- `DISABLED → ARMED`: Requires safety satisfied, E-stop released, no active faults, sensors valid, motor command = 0.
- `ARMED → RUNNING`: Requires explicit `START` command. This is the ONLY path to motor output.
- `RUNNING → DISABLED`: User `STOP` command.
- `ANY → FAULT`: Any critical fault triggers immediate transition. Motor output forced to zero.

## 3. Control Loop Execution (TIM6 ISR, 100 Hz)

```text
1. TimingDiag_MarkStart()
2. Read encoder count (BSP → EncoderDriver)
3. Estimate RPM (SpeedEstimator)
4. Read ADC current (BSP → CurrentMonitor)
5. Evaluate faults (FaultManager)
6. Compute PI output (PI_Controller)
7. Apply safety limits (SafetyLayer)
8. Update motor command (MotorDriver) [DISABLED IN PHASE 3]
9. Store telemetry sample
10. TimingDiag_MarkEnd()
```

## 4. Safety Architecture
The `SafetyLayer` is the **final authority** over motor commands.
- PI controller computes the *requested* command.
- SafetyLayer decides if it is *permitted*.
- Forces output to zero unless system is in `RUNNING` state with no active faults.
- Enforces slew-rate limiting and absolute saturation.

## 5. Watchdog Health Check
The IWDG is NOT blindly refreshed. It requires evidence that BOTH:
1. The TIM6 control-loop ISR has executed since the last refresh.
2. The main loop has processed a telemetry cycle since the last refresh.

If either path stalls (e.g., infinite loop, ISR failure), the watchdog fires and resets the MCU.

## 6. Interrupt Priorities

| IRQ | Priority | Function |
|:---|:---|:---|
| EXTI15_10 (E-Stop) | 0 (Highest) | Immediate motor disable |
| TIM6 (Control Loop) | 1 | Deterministic 100 Hz loop |
| LPUART1 (UART) | 3 | Telemetry (non-critical) |

## 7. Telemetry
- **Format**: ASCII CSV transmitted over LPUART1 at 115200 baud.
- **Fields**: `timestamp,target,measured,error,output,current,state,faults`
- **Rate**: Up to 100 Hz (one sample per control loop tick).
- **Architecture**: ISR writes to a volatile struct; main loop serializes and transmits.
