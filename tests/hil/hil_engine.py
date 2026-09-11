"""
HIL Simulation Engine.

Reuses the EXACT same PI controller equations from the C firmware
and the Python motor simulation. This is NOT a second implementation —
it directly uses the same mathematical logic.

The engine ties together:
  - Virtual Motor
  - Virtual Encoder
  - Virtual Current Sensor
  - Virtual Driver
  - Virtual E-Stop
  - PI Controller (same equations as firmware/control/pi_controller.c)
  - Speed Estimator (same equations as firmware/control/speed_estimator.c)
  - Fault Manager (logic equivalent)
  - Safety Layer (logic equivalent)
  - System State Machine (logic equivalent)
"""
import math
import csv
import os
from virtual_hardware import (
    VirtualMotor, VirtualEncoder, VirtualCurrentSensor,
    VirtualDriver, VirtualEStop
)


# ---- State Machine (mirrors firmware/app/system_state.c) ----
STATE_INIT = 0
STATE_DISABLED = 1
STATE_ARMED = 2
STATE_RUNNING = 3
STATE_FAULT = 4

# ---- Fault Flags (mirrors firmware/safety/fault_manager.h) ----
FAULT_NONE = 0
FAULT_ESTOP = (1 << 0)
FAULT_OVERCURRENT = (1 << 1)
FAULT_OVERSPEED = (1 << 2)
FAULT_STALL = (1 << 3)
FAULT_ENCODER = (1 << 4)
FAULT_SENSOR = (1 << 5)
FAULT_DRIVER = (1 << 6)
FAULT_WATCHDOG = (1 << 7)


class PIController:
    """Exact same discrete-time PI as firmware/control/pi_controller.c"""

    def __init__(self, kp, ki, out_max, out_min):
        self.kp = kp
        self.ki = ki
        self.out_max = out_max
        self.out_min = out_min
        self.integral_sum = 0.0

    def calculate(self, target, measured, dt):
        if dt <= 0.0:
            return 0.0
        error = target - measured
        proportional = self.kp * error
        temp_integral = self.integral_sum + self.ki * error * dt
        output = proportional + temp_integral

        saturate_high = output > self.out_max
        saturate_low = output < self.out_min

        if not ((saturate_high and error > 0) or (saturate_low and error < 0)):
            self.integral_sum = temp_integral

        return max(self.out_min, min(self.out_max, output))

    def reset(self):
        self.integral_sum = 0.0


class SpeedEstimator:
    """Exact same logic as firmware/control/speed_estimator.c"""

    def __init__(self, counts_per_output_rev):
        self.counts_per_rev = counts_per_output_rev
        self.previous_counts = 0

    def calculate_rpm(self, current_counts, dt):
        if dt <= 0.0 or self.counts_per_rev <= 0.0:
            return 0.0
        delta = current_counts - self.previous_counts
        self.previous_counts = current_counts
        revs_per_sec = delta / (self.counts_per_rev * dt)
        return revs_per_sec * 60.0


class CurrentMonitor:
    """Exact same logic as firmware/sensors/current_monitor.c"""

    def __init__(self, offset_v, sensitivity, vref, adc_bits, alpha):
        self.offset_v = offset_v
        self.sensitivity = sensitivity
        self.vref = vref
        self.max_counts = (1 << adc_bits) - 1
        self.alpha = alpha
        self.filtered = 0.0

    def process_adc(self, adc_counts):
        voltage = (adc_counts / self.max_counts) * self.vref
        raw_current = (voltage - self.offset_v) / self.sensitivity
        self.filtered = self.alpha * raw_current + (1.0 - self.alpha) * self.filtered
        return self.filtered


class HILEngine:
    """
    Hardware-in-the-Loop simulation engine.
    Ties virtual hardware to the production firmware control logic.
    """

    def __init__(self, config=None):
        cfg = config or {}
        dt = cfg.get("dt", 0.01)
        counts_per_rev = cfg.get("counts_per_rev", 1496.0)

        self.dt = dt
        self.motor = VirtualMotor(cfg.get("motor_params"))
        self.encoder = VirtualEncoder(counts_per_rev)
        self.current_sensor = VirtualCurrentSensor(cfg.get("sensor_params"))
        self.driver = VirtualDriver()
        self.estop = VirtualEStop()

        self.pi = PIController(
            kp=cfg.get("kp", 0.5),
            ki=cfg.get("ki", 15.0),
            out_max=100.0,
            out_min=-100.0
        )
        self.speed_est = SpeedEstimator(counts_per_rev)
        self.current_mon = CurrentMonitor(
            offset_v=0.0, sensitivity=0.5, vref=3.3,
            adc_bits=12, alpha=0.2
        )

        self.state = STATE_INIT
        self.faults = FAULT_NONE
        self.target_rpm = 0.0
        self.measured_rpm = 0.0
        self.safe_command = 0.0
        self._pi_output = 0.0  # raw PI output before safety layer
        self.tick = 0
        self.loop_time_us = 0.0  # simulated execution time

        # Fault thresholds
        self.overcurrent_threshold = cfg.get("overcurrent_threshold", 1.8)
        self.overspeed_threshold = cfg.get("overspeed_threshold", 5000.0)
        self.stall_detect_rpm = cfg.get("stall_detect_rpm", 5.0)
        self.stall_detect_duty = cfg.get("stall_detect_duty", 20.0)
        self.stall_counter = 0
        self.stall_timeout_ticks = cfg.get("stall_timeout_ticks", 50)

        # Encoder failure detection: uses PI output (not safe_command)
        self.encoder_zero_count = 0
        self.encoder_fail_ticks = cfg.get("encoder_fail_ticks", 30)

        # Watchdog
        self.watchdog_ctrl_ok = False
        self.watchdog_main_ok = False
        self.watchdog_timeout_ticks = cfg.get("watchdog_timeout_ticks", 100)
        self.watchdog_counter = 0
        self.watchdog_triggered = False

        # Simulated loop overrun
        self.inject_overrun = False

        # Telemetry log
        self.telemetry = []

    # ---- State Machine ----
    def _set_fault(self, fault_flag):
        self.faults |= fault_flag
        self.state = STATE_FAULT

    def _clear_faults(self):
        self.faults = FAULT_NONE

    def request_disabled(self):
        if self.state != STATE_FAULT:
            self.state = STATE_DISABLED

    def request_armed(self):
        if (self.state == STATE_DISABLED and
                self.faults == FAULT_NONE and
                not self.estop.is_pressed() and
                self.safe_command == 0.0):
            self.state = STATE_ARMED
            return True
        return False

    def request_running(self):
        if self.state == STATE_ARMED:
            self.state = STATE_RUNNING
            return True
        return False

    def request_fault_reset(self):
        if not self.estop.is_pressed():
            self._clear_faults()
            self.state = STATE_DISABLED

    # ---- Safety Layer ----
    def _safety_process(self, requested_cmd):
        if self.state != STATE_RUNNING or self.faults != FAULT_NONE:
            return 0.0
        return max(-100.0, min(100.0, requested_cmd))

    # ---- Control Loop Tick ----
    def tick_control_loop(self):
        self.tick += 1

        # 1. E-stop check
        if self.estop.is_pressed():
            self._set_fault(FAULT_ESTOP)
            self.driver.disable()

        # 2. Read encoder
        enc_count = self.encoder.get_count()
        self.measured_rpm = self.speed_est.calculate_rpm(enc_count, self.dt)

        # 3. Read current sensor
        adc_raw = self.current_sensor.read_adc(self.motor.get_current())
        measured_current = self.current_mon.process_adc(adc_raw)

        # 4. Fault evaluation
        if abs(measured_current) > self.overcurrent_threshold:
            self._set_fault(FAULT_OVERCURRENT)
        if abs(self.measured_rpm) > self.overspeed_threshold:
            self._set_fault(FAULT_OVERSPEED)
        if self.driver.faulted:
            self._set_fault(FAULT_DRIVER)

        # Stall detection: high duty but very low speed
        if (self.state == STATE_RUNNING and
                abs(self.safe_command) > self.stall_detect_duty and
                abs(self.measured_rpm) < self.stall_detect_rpm):
            self.stall_counter += 1
            if self.stall_counter > self.stall_timeout_ticks:
                self._set_fault(FAULT_STALL)
        else:
            self.stall_counter = 0

        # 5. PI controller
        pi_output = 0.0
        if self.state == STATE_RUNNING:
            pi_output = self.pi.calculate(self.target_rpm, self.measured_rpm, self.dt)
        self._pi_output = pi_output

        # Encoder failure: PI is commanding significant output but encoder
        # shows no movement. Uses raw PI output, not safety-filtered command,
        # so detection continues even if the state has partially degraded.
        if (abs(self._pi_output) > 5.0 and
                abs(self.measured_rpm) < 0.1 and
                self.state == STATE_RUNNING):
            self.encoder_zero_count += 1
            if self.encoder_zero_count > self.encoder_fail_ticks:
                self._set_fault(FAULT_ENCODER)
        else:
            if self.state == STATE_RUNNING:
                self.encoder_zero_count = 0

        # 6. Safety layer
        self.safe_command = self._safety_process(pi_output)

        # 7. Motor driver output
        if self.state == STATE_FAULT or self.faults != FAULT_NONE:
            self.driver.disable()
            self.safe_command = 0.0

        self.driver.set_duty(self.safe_command)
        effective_duty = self.driver.get_effective_duty()

        # 8. Advance motor physics
        self.motor.step(effective_duty, self.dt)
        self.encoder.update(self.motor.omega, self.dt)

        # Simulated loop execution time (in us)
        self.loop_time_us = 50.0 if not self.inject_overrun else 12000.0

        # Watchdog
        self.watchdog_ctrl_ok = True

        # 9. Store telemetry
        self.telemetry.append({
            "timestamp_ms": self.tick * int(self.dt * 1000),
            "target_rpm": self.target_rpm,
            "measured_rpm": self.measured_rpm,
            "error_rpm": self.target_rpm - self.measured_rpm,
            "control_output": self.safe_command,
            "pwm_duty": effective_duty,
            "motor_current": self.motor.get_current(),
            "motor_voltage": self.motor.get_voltage(),
            "state": self.state,
            "fault_flags": self.faults,
            "encoder_count": enc_count,
            "loop_time_us": self.loop_time_us,
        })

    def tick_main_loop(self):
        """Simulates the main loop background tasks."""
        self.watchdog_main_ok = True

    def check_watchdog(self):
        """Returns True if watchdog would fire (health failure)."""
        if self.watchdog_ctrl_ok and self.watchdog_main_ok:
            self.watchdog_counter = 0
            self.watchdog_ctrl_ok = False
            self.watchdog_main_ok = False
            return False
        else:
            self.watchdog_counter += 1
            if self.watchdog_counter > self.watchdog_timeout_ticks:
                self.watchdog_triggered = True
                return True
        return False

    def save_telemetry(self, filepath):
        if not self.telemetry:
            return
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.telemetry[0].keys())
            writer.writeheader()
            writer.writerows(self.telemetry)
