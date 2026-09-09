# Software Architecture
The firmware architecture strictly decouples hardware-independent logic from STM32 peripheral code.

## 1. System State Machine
Implemented in `firmware/app/system_state.h`:
- `INIT` → `DISABLED` (upon boot completion)
- `DISABLED` → `ARMED` (Requires safety satisfied, no active faults, E-stop released, sensors valid, motor command = 0)
- `ARMED` → `RUNNING` (Requires explicit user START command)
- `ANY` → `FAULT` (Triggered by critical hardware or safety failures; forces output to 0)

## 2. Safety Layer
Implemented in `firmware/safety/safety_layer.h`.
The safety layer is the **final authority** over the motor command. It enforces:
- Current system state (0 command if not `RUNNING`).
- Max motor command and saturation.
- Slew-rate limits to prevent mechanical jerking.
The PI controller strictly computes the *requested* command; the safety layer decides if it is *permitted*.

## 3. Telemetry & Commands
- **Telemetry**: Defined as a portable packed C-struct (`TelemetryData_t`). It will be converted by a future UART serialization layer.
- **Commands**: Parsed abstractly (`CommandParser_ParseBuffer`) independent of physical UART interrupts.
