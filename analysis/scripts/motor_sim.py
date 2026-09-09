import math
import csv
import os

class MotorParams:
    def __init__(self):
        self.R = 5.0          
        self.L = 0.005        
        self.Ke = 0.02        
        self.Kt = 0.02        
        self.J = 0.0001       
        self.B = 0.00005      
        self.max_voltage = 12.0
        self.max_current = 2.0

class PIController:
    def __init__(self, kp, ki, out_max, out_min):
        self.kp = kp
        self.ki = ki
        self.out_max = out_max
        self.out_min = out_min
        self.integral_sum = 0.0

    def calculate(self, target, measured, dt):
        error = target - measured
        proportional = self.kp * error
        temp_integral = self.integral_sum + self.ki * error * dt
        output = proportional + temp_integral

        saturate_high = output > self.out_max
        saturate_low = output < self.out_min

        if (saturate_high and error > 0) or (saturate_low and error < 0):
            pass 
        else:
            self.integral_sum = temp_integral

        output = max(self.out_min, min(self.out_max, output))
        return output

def simulate_motor(target_rpm, sim_time, dt, load_torque_step=None, load_torque_time=None):
    params = MotorParams()
    pi = PIController(kp=0.05, ki=0.2, out_max=100.0, out_min=-100.0)

    omega = 0.0 
    current = 0.0 

    counts_per_rev = 1496
    total_angle = 0.0
    results = []

    for step in range(int(sim_time / dt)):
        t = step * dt
        rpm_actual = omega * (60.0 / (2.0 * math.pi))
        measured_rpm = rpm_actual 

        pwm_duty = pi.calculate(target_rpm, measured_rpm, dt)
        applied_voltage = (pwm_duty / 100.0) * params.max_voltage

        t_load = 0.0
        if load_torque_step and load_torque_time and t >= load_torque_time:
            t_load = load_torque_step

        back_emf = params.Ke * omega
        current = (applied_voltage - back_emf) / params.R
        current = max(-params.max_current, min(params.max_current, current))

        motor_torque = params.Kt * current
        domega = (motor_torque - params.B * omega - t_load) / params.J
        
        omega += domega * dt
        total_angle += omega * dt

        results.append({
            "timestamp_ms": int(t * 1000),
            "target_rpm": target_rpm,
            "measured_rpm": measured_rpm,
            "pwm_duty": pwm_duty,
            "current_amps": current,
            "load_torque": t_load
        })

    with open("analysis/data/sim_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp_ms", "target_rpm", "measured_rpm", "pwm_duty", "current_amps", "load_torque"])
        writer.writeheader()
        writer.writerows(results)

if __name__ == "__main__":
    os.makedirs("analysis/data", exist_ok=True)
    os.makedirs("analysis/plots", exist_ok=True)
    simulate_motor(target_rpm=200.0, sim_time=10.0, dt=0.01, load_torque_step=0.01, load_torque_time=1.0)
    print("Simulation complete. Data saved to analysis/data/sim_results.csv")
