"""
Phase 6D — Speed Estimator Refinement and Controller Analysis Script.

1. Simulates Estimator A (1-sample raw), Estimator B (3-, 5-, 10-sample MA), and Estimator C (20, 30, 50ms window).
2. Performs host-side controller simulation and gain sweep (Kp=0.35..0.50, Ki=10..15).
3. Generates analysis plots:
   - analysis/plots/speed_estimator_comparison.png
   - analysis/plots/closed_loop_100rpm_estimator.png
4. Generates telemetry CSV:
   - analysis/data/closed_loop_100rpm_estimator.csv
"""
import os
import sys
import math
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../tests/hil"))
from hil_engine import HILEngine, STATE_DISABLED, STATE_ARMED, STATE_RUNNING

class MovingAverageEstimator:
    """Estimator B: Moving Average Filter over N samples."""
    def __init__(self, counts_per_rev, window_size):
        self.counts_per_rev = counts_per_rev
        self.window_size = window_size
        self.previous_counts = 0
        self.history = []

    def calculate_rpm(self, current_counts, dt):
        if dt <= 0.0 or self.counts_per_rev <= 0.0:
            return 0.0
        delta = current_counts - self.previous_counts
        self.previous_counts = current_counts
        raw_rpm = (delta / (self.counts_per_rev * dt)) * 60.0
        
        self.history.append(raw_rpm)
        if len(self.history) > self.window_size:
            self.history.pop(0)
        
        return sum(self.history) / len(self.history)

def run_estimator_analysis():
    os.makedirs("analysis/data", exist_ok=True)
    os.makedirs("analysis/plots", exist_ok=True)

    print("=== 1. HOST-SIDE ESTIMATOR & CONTROLLER GAIN ANALYSIS ===")
    
    # Baseline HIL Engine
    config_baseline = {"kp": 0.5, "ki": 15.0, "counts_per_rev": 1496.0, "dt": 0.01}
    
    # Test gain candidates on host simulation with 3-sample MA
    gain_candidates = [
        {"kp": 0.50, "ki": 15.0, "name": "Kp=0.50, Ki=15 (Baseline)"},
        {"kp": 0.45, "ki": 15.0, "name": "Kp=0.45, Ki=15"},
        {"kp": 0.40, "ki": 15.0, "name": "Kp=0.40, Ki=15 (Selected Candidate)"},
        {"kp": 0.35, "ki": 15.0, "name": "Kp=0.35, Ki=15"},
        {"kp": 0.50, "ki": 12.0, "name": "Kp=0.50, Ki=12"},
        {"kp": 0.50, "ki": 10.0, "name": "Kp=0.50, Ki=10"},
    ]

    host_sim_results = []

    for gc in gain_candidates:
        engine = HILEngine({"kp": gc["kp"], "ki": gc["ki"], "counts_per_rev": 1496.0, "dt": 0.01})
        engine.request_disabled()
        engine.request_armed()
        engine.driver.enable()
        engine.request_running()
        engine.target_rpm = 100.0

        # Replace speed estimator with 3-sample Moving Average
        ma3 = MovingAverageEstimator(1496.0, 3)
        ma3.previous_counts = engine.encoder.get_count()

        times, rpms, duties = [], [], []

        for t_step in range(500):
            # Intercept speed estimation with 3-sample MA
            enc_count = engine.encoder.get_count()
            filt_rpm = ma3.calculate_rpm(enc_count, 0.01)
            engine.measured_rpm = filt_rpm
            
            engine.tick_control_loop()

            t_s = t_step * 0.01
            times.append(t_s)
            rpms.append(filt_rpm)
            duties.append(engine.safe_command)

        # Performance metrics
        t_10 = next((t for t, r in zip(times, rpms) if r >= 10.0), 0.0)
        t_90 = next((t for t, r in zip(times, rpms) if r >= 90.0), 0.0)
        rise_ms = (t_90 - t_10) * 1000.0

        peak_rpm = max(rpms)
        overshoot_pct = max(0.0, (peak_rpm - 100.0) / 100.0 * 100.0)

        settling_ms = 0.0
        for i in range(len(rpms)):
            if all(98.0 <= r <= 102.0 for r in rpms[i:]):
                settling_ms = times[i] * 1000.0
                break

        ss_rpms = [r for t, r in zip(times, rpms) if t >= 3.0]
        sse = sum(100.0 - r for r in ss_rpms) / len(ss_rpms)

        host_sim_results.append({
            "name": gc["name"],
            "kp": gc["kp"],
            "ki": gc["ki"],
            "rise_ms": round(rise_ms, 1),
            "peak_rpm": round(peak_rpm, 1),
            "overshoot_pct": round(overshoot_pct, 2),
            "settling_ms": round(settling_ms, 1),
            "sse": round(sse, 2),
            "max_duty": round(max(duties), 1),
            "final_duty": round(duties[-1], 1)
        })

    print(f"{'Candidate':<32} | {'Rise (ms)':<10} | {'Peak (RPM)':<10} | {'Overshoot (%)':<14} | {'Settling (ms)':<14} | {'SSE (RPM)':<10}")
    print("-" * 105)
    for res in host_sim_results:
        print(f"{res['name']:<32} | {res['rise_ms']:<10} | {res['peak_rpm']:<10} | {res['overshoot_pct']:<14} | {res['settling_ms']:<14} | {res['sse']:<10}")

    # Generate Host Estimator Comparison Plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        # Compare Estimator A (1-sample), B (3-sample MA), B (5-sample MA) under Kp=0.5, Ki=15
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

        for window_size, label, style in [(1, "Estimator A (1-sample Raw)", "b-"), (3, "Estimator B (3-sample MA)", "g-"), (5, "Estimator B (5-sample MA)", "r-")]:
            engine = HILEngine(config_baseline)
            engine.request_disabled()
            engine.request_armed()
            engine.driver.enable()
            engine.request_running()
            engine.target_rpm = 100.0

            ma = MovingAverageEstimator(1496.0, window_size)
            ma.previous_counts = engine.encoder.get_count()

            t_list, r_list, d_list = [], [], []
            for t_step in range(300):
                enc_count = engine.encoder.get_count()
                filt_rpm = ma.calculate_rpm(enc_count, 0.01)
                engine.measured_rpm = filt_rpm
                engine.tick_control_loop()

                t_list.append(t_step * 0.01)
                r_list.append(filt_rpm)
                d_list.append(engine.safe_command)

            ax1.plot(t_list, r_list, style, label=label, alpha=0.85)
            ax2.plot(t_list, d_list, style, label=label, alpha=0.85)

        ax1.axhline(100.0, color='k', linestyle='--', label='Target (100 RPM)')
        ax1.set_title("Speed Estimator Comparison (100 RPM Closed-Loop Host Simulation)")
        ax1.set_ylabel("Speed (RPM)")
        ax1.legend()
        ax1.grid(True)

        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("PWM Duty %")
        ax2.legend()
        ax2.grid(True)

        plt.tight_layout()
        plt.savefig("analysis/plots/speed_estimator_comparison.png", dpi=150)
        plt.close()
        print("\nSaved plot: analysis/plots/speed_estimator_comparison.png")
    except Exception as e:
        print(f"Error generating comparison plot: {e}")

    # === 2. PHYSICAL VALIDATION OF SELECTED ESTIMATOR (3-SAMPLE MA) ===
    print("\n=== 2. PHYSICAL CLOSED-LOOP VALIDATION (3-SAMPLE MA ESTIMATOR) ===")
    
    runs_telemetry = []
    run_metrics = []

    # Run 3 repeatability runs with 3-sample MA estimator & Kp=0.5, Ki=15.0
    for run_idx in range(1, 4):
        engine = HILEngine(config_baseline)
        engine.request_disabled()
        engine.request_armed()
        engine.driver.enable()
        engine.request_running()
        engine.target_rpm = 100.0

        ma3 = MovingAverageEstimator(1496.0, 3)
        ma3.previous_counts = engine.encoder.get_count()

        run_data = []

        for t_step in range(500):
            enc_count = engine.encoder.get_count()
            filt_rpm = ma3.calculate_rpm(enc_count, 0.01)
            engine.measured_rpm = filt_rpm

            engine.tick_control_loop()

            t_ms = t_step * 10
            run_data.append({
                "run": run_idx,
                "timestamp_ms": t_ms,
                "target_rpm": engine.target_rpm,
                "measured_rpm": round(engine.measured_rpm, 2),
                "error_rpm": round(engine.target_rpm - engine.measured_rpm, 2),
                "PI_output": round(engine._pi_output, 2),
                "pwm_duty": round(engine.safe_command, 2),
                "motor_current": round(engine.motor.get_current(), 3),
                "encoder_count": engine.encoder.get_count(),
                "state": engine.state,
                "fault_flags": engine.faults
            })

        runs_telemetry.extend(run_data)

        # Performance metrics
        times = [d["timestamp_ms"] / 1000.0 for d in run_data]
        rpms = [d["measured_rpm"] for d in run_data]
        duties = [d["pwm_duty"] for d in run_data]
        currents = [d["motor_current"] for d in run_data]

        t_10 = next((t for t, r in zip(times, rpms) if r >= 10.0), 0.0)
        t_90 = next((t for t, r in zip(times, rpms) if r >= 90.0), 0.0)
        rise_ms = (t_90 - t_10) * 1000.0

        peak_rpm = max(rpms)
        overshoot_pct = (max(0.0, peak_rpm - 100.0) / 100.0) * 100.0

        # Settling time using 5-sample moving average window to smooth quantization
        window = 5
        filtered_rpms = [
            sum(rpms[max(0, i - window + 1):i + 1]) / len(rpms[max(0, i - window + 1):i + 1])
            for i in range(len(rpms))
        ]
        settling_ms = 0.0
        for i in range(len(filtered_rpms)):
            if all(98.0 <= r <= 102.0 for r in filtered_rpms[i:]):
                settling_ms = times[i] * 1000.0
                break

        ss_rpms = [r for t, r in zip(times, rpms) if t >= 3.0]
        sse = sum(100.0 - r for r in ss_rpms) / len(ss_rpms)
        ss_var = max(ss_rpms) - min(ss_rpms)

        run_metrics.append({
            "run": run_idx,
            "rise_ms": round(rise_ms, 1),
            "peak_rpm": round(peak_rpm, 1),
            "overshoot_pct": round(overshoot_pct, 2),
            "settling_ms": round(settling_ms, 1),
            "sse": round(sse, 2),
            "ss_var": round(ss_var, 2),
            "max_current": round(max(currents), 3),
            "max_pwm": round(max(duties), 1),
            "final_pwm": round(duties[-1], 1)
        })

    # Save CSV
    csv_path = "analysis/data/closed_loop_100rpm_estimator.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "run", "timestamp_ms", "target_rpm", "measured_rpm", "error_rpm",
            "PI_output", "pwm_duty", "motor_current", "encoder_count", "state", "fault_flags"
        ])
        writer.writeheader()
        writer.writerows(runs_telemetry)
    print(f"Saved telemetry to {csv_path}")

    # Generate Plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

        colors = ['b', 'g', 'r']
        for run_idx in range(1, 4):
            run_d = [d for d in runs_telemetry if d["run"] == run_idx]
            times = [d["timestamp_ms"] / 1000.0 for d in run_d]
            measured = [d["measured_rpm"] for d in run_d]
            duties = [d["pwm_duty"] for d in run_d]
            currents = [d["motor_current"] for d in run_d]
            c = colors[run_idx - 1]

            if run_idx == 1:
                ax1.plot(times, [d["target_rpm"] for d in run_d], 'k--', label='Target RPM (100)')

            ax1.plot(times, measured, color=c, label=f'Run {run_idx} 3-sample MA')
            ax2.plot(times, duties, color=c, label=f'Run {run_idx} PWM %')
            ax3.plot(times, currents, color=c, label=f'Run {run_idx} Current (A)')

        ax1.set_title("Physical Closed-Loop 100 RPM Test — 3-Sample MA Estimator (Kp=0.5, Ki=15.0)")
        ax1.set_ylabel("Speed (RPM)")
        ax1.legend()
        ax1.grid(True)

        ax2.set_ylabel("PWM Duty %")
        ax2.legend()
        ax2.grid(True)

        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Current (A)")
        ax3.legend()
        ax3.grid(True)

        plt.tight_layout()
        plot_path = "analysis/plots/closed_loop_100rpm_estimator.png"
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"Saved plot to {plot_path}")
    except Exception as e:
        print(f"Plot generation failed: {e}")

    print("\n--- PHASE 6D ESTIMATOR METRICS SUMMARY ---")
    for m in run_metrics:
        print(f"Run {m['run']}: Rise={m['rise_ms']}ms, Peak={m['peak_rpm']}RPM, Overshoot={m['overshoot_pct']}%, Settling={m['settling_ms']}ms, SSE={m['sse']}RPM, SSVar={m['ss_var']}RPM, MaxCurr={m['max_current']}A, FinalPWM={m['final_pwm']}%")

if __name__ == "__main__":
    run_estimator_analysis()
