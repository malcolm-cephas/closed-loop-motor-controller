import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import os

# --- Measured Data from Phase 5 ---
measured_duty = np.array([0, 10, 15, 30, 50, 80, 100])
measured_rpm = np.array([0.0, 0.0, 18.5, 75.3, 128.8, 204.6, 248.5])

# --- 1. Plant Identification ---
# Linear region is roughly from 15% to 100% duty
linear_duty = measured_duty[2:]
linear_rpm = measured_rpm[2:]

# Fit a line: RPM = K_gain * (Duty - DeadZone)
# Polyfit of degree 1
coeffs = np.polyfit(linear_duty, linear_rpm, 1)
K_gain = coeffs[0]  # Slope (RPM / %duty)
offset = coeffs[1]
DeadZone_percent = -offset / K_gain

print(f"Identified K_gain: {K_gain:.3f} RPM/%")
print(f"Identified Dead Zone: {DeadZone_percent:.1f}%")

# Generate Model Data
model_duty = np.linspace(0, 100, 100)
model_rpm = np.maximum(0, K_gain * (model_duty - DeadZone_percent))

# Save Plant Identification Data
os.makedirs("analysis/data", exist_ok=True)
os.makedirs("analysis/plots", exist_ok=True)

with open("analysis/data/plant_identification.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["duty_percent", "measured_rpm", "model_rpm"])
    for d in model_duty:
        # Interpolate measured for comparison
        m = np.interp(d, measured_duty, measured_rpm)
        mod = max(0, K_gain * (d - DeadZone_percent))
        writer.writerow([d, m, mod])

# Plot Measured vs Model
plt.figure(figsize=(8, 5))
plt.plot(measured_duty, measured_rpm, 'ro', label='Measured Data')
plt.plot(model_duty, model_rpm, 'b-', label=f'Model: {K_gain:.2f}*(Duty-{DeadZone_percent:.1f}%)')
plt.xlabel('PWM Duty (%)')
plt.ylabel('Speed (RPM)')
plt.title('DC Motor Plant Identification (Steady State)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig('analysis/plots/measured_vs_model.png')
plt.close()

# --- 2. PI Tuning Sweep ---
# Time constant tau ~ 0.08 s (since settling time is ~250ms, approx 3*tau)
tau = 0.08
dt = 0.01  # 10ms control loop

# We will simulate a step response for various Kp, Ki combinations
# using the newly identified plant model.

def sim_closed_loop(Kp, Ki, target_rpm=128.8, sim_time=1.0):
    steps = int(sim_time / dt)
    rpm = 0.0
    integral = 0.0
    
    time_arr = []
    rpm_arr = []
    
    for i in range(steps):
        error = target_rpm - rpm
        
        # PI Control
        proportional = Kp * error
        temp_integral = integral + Ki * error * dt
        cmd_duty = proportional + temp_integral
        
        # Anti-windup and Saturation
        sat_duty = max(-100.0, min(100.0, cmd_duty))
        
        saturate_high = cmd_duty > 100.0
        saturate_low = cmd_duty < -100.0
        if not ((saturate_high and error > 0) or (saturate_low and error < 0)):
            integral = temp_integral
            
        # Plant Dynamics (First-order + Deadzone)
        # Apply deadzone
        effective_duty = 0.0
        if sat_duty > DeadZone_percent:
            effective_duty = sat_duty - DeadZone_percent
        elif sat_duty < -DeadZone_percent:
            effective_duty = sat_duty + DeadZone_percent
            
        ss_rpm = K_gain * effective_duty
        
        # Euler integration for time constant
        rpm += (ss_rpm - rpm) * (dt / tau)
        
        time_arr.append(i * dt)
        rpm_arr.append(rpm)
        
    return time_arr, rpm_arr

# Candidate Gains
gains = [
    (0.1, 1.0),
    (0.2, 2.0),
    (0.4, 4.0),
    (0.8, 8.0)
]

plt.figure(figsize=(10, 6))
for Kp, Ki in gains:
    t, r = sim_closed_loop(Kp, Ki)
    plt.plot(t, r, label=f'Kp={Kp}, Ki={Ki}')

plt.axhline(128.8, color='k', linestyle='--', label='Target (128.8 RPM)')
plt.xlabel('Time (s)')
plt.ylabel('Speed (RPM)')
plt.title('PI Tuning Sweep on Identified Plant (Step to 50% Speed)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig('analysis/plots/pi_tuning_real_plant.png')
plt.close()

print("Plant identification and PI tuning complete. Plots generated.")
