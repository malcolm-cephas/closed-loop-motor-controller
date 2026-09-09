import csv
import numpy as np
import matplotlib.pyplot as plt

def analyze_performance(csv_file, ss_window_percent=10.0):
    times = []
    targets = []
    measured = []
    load_torques = []

    try:
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                times.append(float(row["timestamp_ms"]) / 1000.0)
                targets.append(float(row["target_rpm"]))
                measured.append(float(row["measured_rpm"]))
                load_torques.append(float(row.get("load_torque", 0.0)))
    except FileNotFoundError:
        print(f"Error: {csv_file} not found.")
        return

    if not times:
        return

    times = np.array(times)
    targets = np.array(targets)
    measured = np.array(measured)
    load_torques = np.array(load_torques)

    final_target = targets[-1]
    sim_duration = times[-1]
    
    # 1. INITIAL STEP RESPONSE
    disturbance_start_idx = np.where(load_torques > 0)[0]
    if len(disturbance_start_idx) > 0:
        dist_idx = disturbance_start_idx[0]
        dist_time = times[dist_idx]
    else:
        dist_idx = len(times) - 1
        dist_time = times[-1]

    initial_times = times[:dist_idx]
    initial_measured = measured[:dist_idx]

    peak_rpm = np.max(initial_measured)
    overshoot = max(0.0, (peak_rpm - final_target) / final_target * 100.0) if final_target > 0 else 0

    t_10 = next((t for t, m in zip(initial_times, initial_measured) if m >= 0.1 * final_target), None)
    t_90 = next((t for t, m in zip(initial_times, initial_measured) if m >= 0.9 * final_target), None)
    rise_time = (t_90 - t_10) if (t_10 is not None and t_90 is not None) else float('inf')

    initial_settling_time = float('inf')
    for t, m in reversed(list(zip(initial_times, initial_measured))):
        if abs(m - final_target) > 0.02 * final_target:
            initial_settling_time = t
            break

    print("--- Initial Step Response ---")
    print(f"Rise Time: {rise_time:.3f} s")
    print(f"Overshoot: {overshoot:.1f}%")
    print(f"Settling Time: {initial_settling_time:.3f} s")
    print(f"Peak RPM: {peak_rpm:.2f}")

    # 2. LOAD DISTURBANCE RESPONSE
    if dist_time < sim_duration:
        rpm_before_dist = initial_measured[-1] if len(initial_measured) > 0 else 0
        dist_measured = measured[dist_idx:]
        dist_times = times[dist_idx:]
        
        min_rpm_after_dist = np.min(dist_measured)
        speed_drop = rpm_before_dist - min_rpm_after_dist
        
        dist_recovery_time = float('inf')
        # Find when it enters the 2% band and stays there
        for t, m in reversed(list(zip(dist_times, dist_measured))):
            if abs(m - final_target) > 0.02 * final_target:
                dist_recovery_time = t - dist_time
                break

        print("\n--- Load Disturbance Response ---")
        print(f"Speed Drop: {speed_drop:.2f} RPM (Min RPM: {min_rpm_after_dist:.2f})")
        print(f"Recovery Time: {dist_recovery_time:.3f} s")
    else:
        print("\n--- No Load Disturbance Detected ---")

    # 3. STEADY-STATE EVALUATION
    ss_duration = sim_duration * (ss_window_percent / 100.0)
    ss_start_time = sim_duration - ss_duration
    
    ss_mask = times >= ss_start_time
    ss_measured = measured[ss_mask]
    
    ss_mean_rpm = np.mean(ss_measured)
    ss_error = abs(final_target - ss_mean_rpm)
    ss_std = np.std(ss_measured)
    ss_max_dev = np.max(np.abs(ss_measured - ss_mean_rpm))
    
    print(f"Final Mean RPM: {ss_mean_rpm:.2f}")
    print(f"Steady-State Error: {ss_error:.2f} RPM")
    print(f"Steady-State Variation: ±{ss_max_dev:.2f} RPM (StdDev: {ss_std:.3f})")

    # 4. PLOTTING
    plt.figure(figsize=(10, 6))
    plt.plot(times, measured, label="Measured RPM", color='blue')
    plt.axhline(y=final_target, color='r', linestyle='--', label="Target RPM")
    
    # 2% settling bands
    plt.axhline(y=final_target * 1.02, color='gray', linestyle=':', alpha=0.5, label="±2% Band")
    plt.axhline(y=final_target * 0.98, color='gray', linestyle=':', alpha=0.5)

    # Annotate times
    plt.axvline(x=0, color='green', linestyle='-.', alpha=0.3, label="Initial Command")
    if dist_time < sim_duration:
        plt.axvline(x=dist_time, color='orange', linestyle='-.', alpha=0.6, label="Load Disturbance")
    
    # Steady state window shading
    plt.axvspan(ss_start_time, sim_duration, color='purple', alpha=0.1, label="Steady-State Eval Window")

    plt.xlabel('Time (s)')
    plt.ylabel('RPM')
    plt.title('Motor Control Step & Disturbance Response')
    plt.legend(loc='lower right')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('analysis/plots/performance_plot.png')
    print("\nPlot saved to analysis/plots/performance_plot.png")

if __name__ == "__main__":
    analyze_performance("analysis/data/sim_results.csv", ss_window_percent=10.0)
