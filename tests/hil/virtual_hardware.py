"""
Virtual Hardware Models for HIL Testing.

These models simulate the physical hardware components (motor, encoder,
current sensor, driver) so that the production firmware control logic
can be exercised without real hardware.

ALL PARAMETERS ARE SIMULATION ASSUMPTIONS — NOT MEASURED HARDWARE VALUES.
"""
import math


class VirtualMotor:
    """
    Simplified DC motor model using electrical and mechanical equations.

    Electrical (steady-state approximation, neglecting L):
        I = (V_applied - Ke * omega) / R

    Mechanical:
        J * d(omega)/dt = Kt * I - B * omega - T_load

    Parameters are explicitly configurable and labeled as assumptions.
    """

    def __init__(self, params=None):
        p = params or {}
        # Identified parameters to match ~2.66 RPM/%, ~80ms time constant, ~15% startup
        self.R = p.get("resistance", 10.0)           # Ohm [UPDATED via ID]
        self.Ke = p.get("ke", 0.045)                 # V/(rad/s) [UPDATED via ID]
        self.Kt = p.get("kt", 0.045)                 # Nm/A [UPDATED via ID]
        self.J = p.get("inertia", 0.00005)           # kg*m^2 [UPDATED via ID]
        self.B = p.get("friction", 0.0001)           # Nm/(rad/s) [UPDATED via ID]
        self.V_supply = p.get("supply_voltage", 12.0)
        self.I_max = p.get("max_current", 2.0)
        self.stiction_torque = p.get("stiction", 0.005) # Nm to simulate deadzone

        self.omega = 0.0      # rad/s
        self.current = 0.0    # A
        self.voltage = 0.0    # V applied to motor
        self.load_torque = 0.0  # Nm

    def set_load_torque(self, torque_nm):
        self.load_torque = torque_nm

    def step(self, duty_percent, dt):
        """Advance the motor model by one time step."""
        self.voltage = (duty_percent / 100.0) * self.V_supply
        back_emf = self.Ke * self.omega
        self.current = (self.voltage - back_emf) / self.R
        self.current = max(-self.I_max, min(self.I_max, self.current))

        motor_torque = self.Kt * self.current
        
        # Apply stiction (deadzone)
        net_torque = motor_torque - self.load_torque
        if abs(self.omega) < 0.1:  # almost stopped
            if abs(net_torque) <= self.stiction_torque:
                domega = 0.0
                self.omega = 0.0
            else:
                effective_torque = net_torque - math.copysign(self.stiction_torque, net_torque)
                domega = (effective_torque - self.B * self.omega) / self.J
                self.omega += domega * dt
        else:
            domega = (net_torque - self.B * self.omega) / self.J
            self.omega += domega * dt

    def get_rpm(self):
        return self.omega * (60.0 / (2.0 * math.pi))

    def get_current(self):
        return self.current

    def get_voltage(self):
        return self.voltage


class VirtualEncoder:
    """
    Virtual quadrature encoder that generates a cumulative count from
    the motor's angular position.

    counts_per_output_rev is CONFIGURABLE — not hard-coded to 1496.
    """

    def __init__(self, counts_per_output_rev=1496.0):
        self.counts_per_output_rev = counts_per_output_rev
        self.fractional_angle_rev = 0.0  # accumulated revolutions (float)

    def update(self, omega, dt):
        """Accumulate angle from angular velocity."""
        revolutions_this_step = (omega / (2.0 * math.pi)) * dt
        self.fractional_angle_rev += revolutions_this_step

    def get_count(self):
        """Return integer encoder count (quantized)."""
        return int(self.fractional_angle_rev * self.counts_per_output_rev)

    def reset(self):
        self.fractional_angle_rev = 0.0


class VirtualCurrentSensor:
    """
    Virtual INA169-style current sensor.

    Converts motor current to a simulated ADC count.
    Scaling, offset, and noise are CONFIGURABLE.
    """

    def __init__(self, params=None):
        p = params or {}
        self.sensitivity = p.get("sensitivity_v_per_a", 0.5)  # [ASSUMPTION]
        self.offset_v = p.get("offset_v", 0.0)
        self.vref = p.get("vref", 3.3)
        self.adc_bits = p.get("adc_bits", 12)
        self.noise_amplitude = p.get("noise_amplitude", 0.0)  # Volts of noise

        self._rng_state = 42  # Deterministic seed for reproducibility

    def _simple_noise(self):
        """Simple deterministic pseudo-random noise for reproducibility."""
        self._rng_state = (self._rng_state * 1103515245 + 12345) & 0x7FFFFFFF
        return ((self._rng_state / 0x7FFFFFFF) - 0.5) * 2.0 * self.noise_amplitude

    def read_adc(self, actual_current):
        """Convert actual motor current to simulated ADC count."""
        voltage = self.offset_v + self.sensitivity * abs(actual_current)
        voltage += self._simple_noise()
        voltage = max(0.0, min(self.vref, voltage))
        max_counts = (1 << self.adc_bits) - 1
        return int((voltage / self.vref) * max_counts)


class VirtualDriver:
    """
    Virtual BTS7960 motor driver.

    Models the enable state and fault conditions.
    When disabled or faulted, effective duty is forced to 0.
    """

    def __init__(self):
        self.enabled = False
        self.faulted = False
        self.commanded_duty = 0.0

    def enable(self):
        if not self.faulted:
            self.enabled = True

    def disable(self):
        self.enabled = False

    def set_fault(self, faulted):
        self.faulted = faulted
        if faulted:
            self.enabled = False

    def set_duty(self, duty_percent):
        self.commanded_duty = duty_percent

    def get_effective_duty(self):
        """Returns the actual duty applied to the motor."""
        if not self.enabled or self.faulted:
            return 0.0
        return self.commanded_duty


class VirtualEStop:
    """Virtual E-stop button."""

    def __init__(self):
        self.pressed = False

    def press(self):
        self.pressed = True

    def release(self):
        self.pressed = False

    def is_pressed(self):
        return self.pressed
