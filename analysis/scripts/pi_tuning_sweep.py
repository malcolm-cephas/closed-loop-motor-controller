import math
import itertools
import numpy as np
import matplotlib.pyplot as plt

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

        if not ((saturate_high and error > 0) or (saturate_low and error < 0)):
            self.integral_sum = temp_integral

        return max(self.out_min, min(self.out_max, output))

def simulate(kp, ki, params, sim_time=5.0, dt=0.01, target_rpm=200.0, load_torque_step=0.01, load_torque_time=1.0):
    pi = PIController(kp, ki, 100.0, -100.0)
    omega = 0.0 
    counts_per_rev = 1496
    total_angle = 0.0

    times = []
    measured = []
    
    for step in range(int(sim_time / dt)):
        t = step * dt
        rpm_actual = omega * (60.0 / (2.0 * math.pi))
        
        # Quantization
        revolutions = total_angle / (2.0 * math.pi)
        counts = int(revolutions * counts_per_rev)
        measured_rpm = (counts / counts_per_rev) * (60.0 / (2.0 * math.pi)) # Simplified for sim speed, actually just use rpm_actual
        measured_rpm = rpm_actual

        pwm_duty = pi.calculate(target_rpm, measured_rpm, dt)
        applied_voltage = (pwm_duty / 100.0) * params.max_voltage

        t_load = load_torque_step if t >= load_torque_time else 0.0
        back_emf = params.Ke * omega
        current = (applied_voltage - back_emf) / params.R
        current = max(-params.max_current, min(params.max_current, current))
        
        motor_torque = params.Kt * current
        domega = (motor_torque - params.B * omega - t_load) / params.J
        
        omega += domega * dt
        total_angle += omega * dt

        times.append(t)
        measured.append(measured_rpm)
        
    return np.array(times), np.array(measured)

def evaluate_metrics(times, measured, target_rpm, dist_time=1.0):
    dist_idx = np.searchsorted(times, dist_time)
    
    initial_measured = measured[:dist_idx]
    peak_rpm = np.max(initial_measured)
    overshoot = max(0.0, (peak_rpm - target_rpm) / target_rpm * 100.0)
    
    t_10 = next((t for t, m in zip(times[:dist_idx], initial_measured) if m >= 0.1 * target_rpm), None)
    t_90 = next((t for t, m in zip(times[:dist_idx], initial_measured) if m >= 0.9 * target_rpm), None)
    rise_time = (t_90 - t_10) if (t_10 is not None and t_90 is not None) else 999.0
    
    settling_time = 999.0
    for t, m in reversed(list(zip(times[:dist_idx], initial_measured))):
        if abs(m - target_rpm) > 0.02 * target_rpm:
            settling_time = t
            break
            
    rpm_before_dist = initial_measured[-1]
    dist_measured = measured[dist_idx:]
    min_after_dist = np.min(dist_measured)
    speed_drop = rpm_before_dist - min_after_dist
    
    recovery_time = 999.0
    for t, m in reversed(list(zip(times[dist_idx:], dist_measured))):
        if abs(m - target_rpm) > 0.02 * target_rpm:
            recovery_time = t - dist_time
            break
            
    final_ss = np.mean(measured[-int(len(measured)*0.1):])
    sse = abs(target_rpm - final_ss)
    
    return rise_time, overshoot, settling_time, speed_drop, recovery_time, sse

def score_metrics(overshoot, settling, recovery, sse, rise_time):
    # Penalties
    cost = 0
    if overshoot > 5.0: cost += (overshoot - 5.0) * 100
    if settling > 0.5: cost += (settling - 0.5) * 500
    if sse > 4.0: cost += (sse - 4.0) * 500
    
    cost += overshoot * 5
    cost += settling * 50
    cost += recovery * 50
    cost += sse * 20
    cost += rise_time * 10
    return cost

def run_sweep():
    kps = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
    kis = [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
    
    results = []
    base_params = MotorParams()
    
    for kp, ki in itertools.product(kps, kis):
        times, measured = simulate(kp, ki, base_params, sim_time=5.0)
        rt, ov, st, drop, rec, sse = evaluate_metrics(times, measured, 200.0)
        
        # Reject unstable (NaN or massive values)
        if math.isnan(ov) or math.isnan(sse) or ov > 100.0 or sse > 100.0:
            continue
            
        score = score_metrics(ov, st, rec, sse, rt)
        results.append((kp, ki, rt, ov, st, drop, rec, sse, score))
        
    results.sort(key=lambda x: x[-1])
    return results

def run_robustness(kp, ki):
    cases = [
        ("Nominal", MotorParams()),
        ("Inertia +20%", MotorParams()),
        ("Inertia -20%", MotorParams()),
        ("Friction +20%", MotorParams()),
        ("Friction -20%", MotorParams()),
        ("Resistance +10%", MotorParams()),
        ("Load +20%", MotorParams())
    ]
    
    cases[1][1].J *= 1.2
    cases[2][1].J *= 0.8
    cases[3][1].B *= 1.2
    cases[4][1].B *= 0.8
    cases[5][1].R *= 1.1
    
    worst_ov = 0
    worst_st = 0
    worst_rec = 0
    worst_sse = 0
    
    print("\nRobustness Tests (Kp={}, Ki={})".format(kp, ki))
    for name, params in cases:
        load = 0.012 if name == "Load +20%" else 0.01
        times, measured = simulate(kp, ki, params, load_torque_step=load)
        rt, ov, st, drop, rec, sse = evaluate_metrics(times, measured, 200.0)
        print(f"{name:15}: OV={ov:5.1f}% ST={st:5.3f}s REC={rec:5.3f}s SSE={sse:5.2f}")
        worst_ov = max(worst_ov, ov)
        worst_st = max(worst_st, st)
        worst_rec = max(worst_rec, rec)
        worst_sse = max(worst_sse, sse)
        
    return worst_ov, worst_st, worst_rec, worst_sse

if __name__ == "__main__":
    print("Running PI Parameter Sweep...")
    results = run_sweep()
    
    print("\n--- TOP 10 CANDIDATES ---")
    print(f"{'Kp':<5} | {'Ki':<5} | {'Rise(s)':<7} | {'Over(%)':<7} | {'Settl(s)':<8} | {'Recov(s)':<8} | {'SSE(rpm)':<8} | {'Score':<8}")
    for r in results[:10]:
        print(f"{r[0]:<5.2f} | {r[1]:<5.2f} | {r[2]:<7.3f} | {r[3]:<7.1f} | {r[4]:<8.3f} | {r[6]:<8.3f} | {r[7]:<8.2f} | {r[8]:<8.1f}")
        
    best = results[0]
    best_kp, best_ki = best[0], best[1]
    
    worst_ov, worst_st, worst_rec, worst_sse = run_robustness(best_kp, best_ki)
    
    print("\n--- FINAL COMPARISON ---")
    print("Baseline: Kp=0.05, Ki=0.20")
    print(f"Best Sim: Kp={best_kp:.2f}, Ki={best_ki:.2f}")
    
    # Plotting
    base_params = MotorParams()
    times_base, meas_base = simulate(0.05, 0.2, base_params, sim_time=5.0)
    times_best, meas_best = simulate(best_kp, best_ki, base_params, sim_time=5.0)
    
    plt.figure(figsize=(10, 6))
    plt.plot(times_base, meas_base, label="Baseline (Kp=0.05, Ki=0.2)", color='blue', alpha=0.5)
    plt.plot(times_best, meas_best, label=f"Best Candidate (Kp={best_kp}, Ki={best_ki})", color='red')
    plt.axhline(200.0, color='black', linestyle='--', label='Target')
    plt.title('Baseline vs Best Simulated Candidate')
    plt.xlabel('Time (s)')
    plt.ylabel('RPM')
    plt.legend()
    plt.grid(True)
    plt.savefig('analysis/plots/tuning_comparison.png')
    print("Plot saved to analysis/plots/tuning_comparison.png")
