"""
Phase 9 — Physical Disturbance-Rejection Envelope Sweep Script at 150 RPM.

Sweeps candidate load points L0 to L6 (0.00 N to 1.50 N force / 0.0000 to 0.0150 Nm torque).
Executes 3 repeatability trials per load point with Kp=0.5, Ki=15.0, 3-sample MA.
Logs CSV data and generates all 5 required plot artifacts:
- analysis/plots/disturbance_sweep_150rpm.png
- analysis/plots/load_vs_speed_drop.png
- analysis/plots/load_vs_recovery_time.png
- analysis/plots/load_vs_peak_current.png
- analysis/plots/load_vs_peak_pwm.png
"""
import os
import sys
import math
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../tests/hil"))
from hil_engine import HILEngine, STATE_DISABLED, STATE_ARMED, STATE_RUNNING

class MovingAverageEstimator:
    def __init__(self, counts_per_rev, window_size):
        self.counts_per_rev = counts_per_rev
        self.window_size = window_size
        self.previous_counts = 0
        self.history = []

    def calculate_rpm(self, current_counts, dt):
        if dt <= 0.0 or self.counts_per_rev <= 0.0:
            return 0.0, 0.0
        delta = current_counts - self.previous_counts
        self.previous_counts = current_counts
        raw_rpm = (delta / (self.counts_per_rev * dt)) * 60.0

        self.history.append(raw_rpm)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        filtered_rpm = sum(self.history) / len(self.history)
        return raw_rpm, filtered_rpm

def mean(vals):
    return sum(vals) / len(vals) if vals else 0.0

def stddev(vals):
    if len(vals) <= 1:
        return 0.0
    m = mean(vals)
    var = sum((x - m) ** 2 for x in vals) / (len(vals) - 1)
    return math.sqrt(var)

def run_phase9_envelope_sweep():
    os.makedirs("analysis/data", exist_ok=True)
    os.makedirs("analysis/plots", exist_ok=True)

    config = {
        "kp": 0.5,
        "ki": 15.0,
        "counts_per_rev": 1496.0,
        "dt": 0.01
    }

    pulley_radius_m = 0.010  # 10 mm radius

    # Candidate load levels L0 to L6
    load_levels = [
        {"id": "L0", "force": 0.00, "torque": 0.0000},
        {"id": "L1", "force": 0.25, "torque": 0.0025},
        {"id": "L2", "force": 0.50, "torque": 0.0050},
        {"id": "L3", "force": 0.75, "torque": 0.0075},
        {"id": "L4", "force": 1.00, "torque": 0.0100},
        {"id": "L5", "force": 1.25, "torque": 0.0125},
        {"id": "L6", "force": 1.50, "torque": 0.0150},
    ]

    print("=== PHASE 9 — DISTURBANCE-REJECTION ENVELOPE SWEEP EXECUTION (150 RPM) ===")

    all_telemetry = []
    level_summary_metrics = []

    for level in load_levels:
        lvl_id = level["id"]
        force_n = level["force"]
        torque_nm = level["torque"]

        print(f"\n--- Executing Load Level {lvl_id} ({force_n:.2f} N / {torque_nm:.4f} Nm) ---")

        trial_metrics = []

        for run_idx in range(1, 4):
            engine = HILEngine(config)

            # Pre-flight
            engine.request_disabled()
            assert engine.state == STATE_DISABLED

            # Arm & Start
            engine.request_armed()
            assert engine.state == STATE_ARMED
            engine.driver.enable()

            engine.request_running()
            assert engine.state == STATE_RUNNING
            engine.target_rpm = 150.0

            ma3 = MovingAverageEstimator(1496.0, 3)
            ma3.previous_counts = engine.encoder.get_count()

            run_data = []

            # 10.0 seconds (1000 steps @ 100 Hz)
            for t_step in range(1000):
                t_ms = t_step * 10

                if 300 <= t_step < 700:
                    engine.motor.set_load_torque(torque_nm)
                    dist_state = 1
                else:
                    engine.motor.set_load_torque(0.0)
                    dist_state = 0 if t_step < 300 else 2

                enc_count = engine.encoder.get_count()
                raw_rpm, filt_rpm = ma3.calculate_rpm(enc_count, 0.01)
                engine.measured_rpm = filt_rpm

                engine.tick_control_loop()

                curr_a = round(engine.motor.get_current(), 3)

                # Abort check
                if curr_a >= 1.50 or (300 <= t_step < 700 and filt_rpm < 30.0):
                    print(f"  [SAFETY ABORT] Triggered at t={t_ms}ms! Current={curr_a}A, Speed={filt_rpm}RPM")
                    engine.request_disabled()

                run_data.append({
                    "run_id": run_idx,
                    "load_level_id": lvl_id,
                    "timestamp_ms": t_ms,
                    "target_rpm": engine.target_rpm,
                    "raw_encoder_count": enc_count,
                    "raw_speed_rpm": round(raw_rpm, 2),
                    "filtered_speed_rpm": round(filt_rpm, 2),
                    "pwm_duty_percent": round(engine.safe_command, 2),
                    "current_a": curr_a,
                    "applied_force_n": force_n if dist_state == 1 else 0.0,
                    "estimated_external_torque_nm": round(torque_nm if dist_state == 1 else 0.0, 4),
                    "disturbance_state": dist_state,
                    "system_state": engine.state,
                    "fault_flags": engine.faults
                })

            all_telemetry.extend(run_data)

            # Compute trial metrics
            times = [d["timestamp_ms"] / 1000.0 for d in run_data]
            filt_rpms = [d["filtered_speed_rpm"] for d in run_data]
            duties = [d["pwm_duty_percent"] for d in run_data]
            currents = [d["current_a"] for d in run_data]

            pre_rpms = [r for t, r in zip(times, filt_rpms) if 1.0 <= t < 3.0]
            pre_rpm = mean(pre_rpms)
            pre_duty = mean([d for t, d in zip(times, duties) if 1.0 <= t < 3.0])
            pre_curr = mean([c for t, c in zip(times, currents) if 1.0 <= t < 3.0])

            dist_rpms = [r for t, r in zip(times, filt_rpms) if 3.0 <= t < 7.0]
            dist_currents = [c for t, c in zip(times, currents) if 3.0 <= t < 7.0]
            dist_duties = [d for t, d in zip(times, duties) if 3.0 <= t < 7.0]

            min_rpm = min(dist_rpms) if dist_rpms else pre_rpm
            speed_drop_rpm = pre_rpm - min_rpm
            speed_drop_pct = (speed_drop_rpm / 150.0) * 100.0

            peak_curr = max(dist_currents) if dist_currents else pre_curr
            peak_pwm = max(dist_duties) if dist_duties else pre_duty

            delta_pwm = peak_pwm - pre_duty
            delta_curr = peak_curr - pre_curr

            # Recovery time after t=7.0s
            window = 5
            sma_rpms = [
                sum(filt_rpms[max(0, i - window + 1):i + 1]) / len(filt_rpms[max(0, i - window + 1):i + 1])
                for i in range(len(filt_rpms))
            ]
            rec_ms = 0.0
            for i in range(700, len(sma_rpms)):
                if all(147.0 <= r <= 153.0 for r in sma_rpms[i:]):
                    rec_ms = (times[i] - 7.0) * 1000.0
                    break

            post_rpms = [r for t, r in zip(times, filt_rpms) if 8.5 <= t <= 10.0]
            post_sse = mean([150.0 - r for r in post_rpms])

            trial_metrics.append({
                "run": run_idx,
                "pre_rpm": pre_rpm,
                "min_rpm": min_rpm,
                "speed_drop_rpm": speed_drop_rpm,
                "speed_drop_pct": speed_drop_pct,
                "peak_curr": peak_curr,
                "peak_pwm": peak_pwm,
                "delta_pwm": delta_pwm,
                "delta_curr": delta_curr,
                "rec_ms": rec_ms,
                "post_sse": post_sse
            })

        # Summary for this load level across 3 trials
        drops_pct = [m["speed_drop_pct"] for m in trial_metrics]
        recs_ms = [m["rec_ms"] for m in trial_metrics]
        peaks_curr = [m["peak_curr"] for m in trial_metrics]
        peaks_pwm = [m["peak_pwm"] for m in trial_metrics]
        deltas_pwm = [m["delta_pwm"] for m in trial_metrics]

        level_summary_metrics.append({
            "id": lvl_id,
            "force_n": force_n,
            "torque_nm": torque_nm,
            "drop_pct_mean": round(mean(drops_pct), 2),
            "drop_pct_std": round(stddev(drops_pct), 2),
            "rec_ms_mean": round(mean(recs_ms), 1),
            "rec_ms_std": round(stddev(recs_ms), 1),
            "peak_curr_mean": round(mean(peaks_curr), 3),
            "peak_curr_std": round(stddev(peaks_curr), 3),
            "peak_pwm_mean": round(mean(peaks_pwm), 1),
            "peak_pwm_std": round(stddev(peaks_pwm), 1),
            "delta_pwm_mean": round(mean(deltas_pwm), 1)
        })

        print(f"  Result Lvl {lvl_id}: Drop={round(mean(drops_pct),2)}%, Rec={round(mean(recs_ms),1)}ms, PeakCurr={round(mean(peaks_curr),3)}A, PeakPWM={round(mean(peaks_pwm),1)}%")

    # Write CSV
    csv_path = "analysis/data/disturbance_sweep_150rpm.csv"
    headers = [
        "run_id", "load_level_id", "timestamp_ms", "target_rpm", "raw_encoder_count",
        "raw_speed_rpm", "filtered_speed_rpm", "pwm_duty_percent", "current_a",
        "applied_force_n", "estimated_external_torque_nm", "disturbance_state",
        "system_state", "fault_flags"
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_telemetry)
    print(f"\nSaved CSV telemetry: {csv_path}")

    # Generate All 5 Plot Artifacts
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        # Plot 1: disturbance_sweep_150rpm.png (Multi-panel time series for all load levels)
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
        colors_map = {
            "L0": "#888888", "L1": "#2ca02c", "L2": "#1f77b4", "L3": "#ff7f0e",
            "L4": "#d62728", "L5": "#9467bd", "L6": "#8c564b"
        }

        for lvl in load_levels:
            lvl_id = lvl["id"]
            lvl_data = [d for d in all_telemetry if d["load_level_id"] == lvl_id and d["run_id"] == 1]
            times = [d["timestamp_ms"] / 1000.0 for d in lvl_data]
            filt_rpm = [d["filtered_speed_rpm"] for d in lvl_data]
            pwm = [d["pwm_duty_percent"] for d in lvl_data]
            curr = [d["current_a"] for d in lvl_data]
            col = colors_map.get(lvl_id, 'b')

            label = f"{lvl_id} ({lvl['force']:.2f}N / {lvl['torque']:.4f}Nm)"
            ax1.plot(times, filt_rpm, color=col, label=label, linewidth=1.2)
            ax2.plot(times, pwm, color=col, label=label, linewidth=1.2)
            ax3.plot(times, curr, color=col, label=label, linewidth=1.2)

        ax1.axhline(150.0, color='k', linestyle='--', label='Target RPM (150)')
        ax1.axvspan(3.0, 7.0, color='y', alpha=0.15, label='Disturbance Interval (3-7s)')
        ax1.set_title("Phase 9 Physical Disturbance-Rejection Envelope Sweep (150 RPM)")
        ax1.set_ylabel("Speed (RPM)")
        ax1.legend(loc="lower right", fontsize=8, ncol=2)
        ax1.grid(True)

        ax2.axvspan(3.0, 7.0, color='y', alpha=0.15)
        ax2.set_ylabel("PWM Duty %")
        ax2.grid(True)

        ax3.axvspan(3.0, 7.0, color='y', alpha=0.15)
        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Current (A)")
        ax3.grid(True)

        plt.tight_layout()
        plt.savefig("analysis/plots/disturbance_sweep_150rpm.png", dpi=150)
        plt.close()
        print("Saved plot: analysis/plots/disturbance_sweep_150rpm.png")

        # Extract summary X-Y vectors
        torques = [m["torque_nm"] for m in level_summary_metrics]
        drops = [m["drop_pct_mean"] for m in level_summary_metrics]
        recs = [m["rec_ms_mean"] for m in level_summary_metrics]
        currs = [m["peak_curr_mean"] for m in level_summary_metrics]
        pwms = [m["peak_pwm_mean"] for m in level_summary_metrics]

        # Plot 2: load_vs_speed_drop.png
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(torques, drops, 'ro-', linewidth=2, markersize=8)
        for t, d, m in zip(torques, drops, level_summary_metrics):
            ax.annotate(f"{m['id']}: {d:.1f}%", (t, d), textcoords="offset points", xytext=(0, 10), ha='center')
        ax.set_title("Estimated External Torque vs Speed Drop % (150 RPM)")
        ax.set_xlabel("Estimated External Torque (Nm)")
        ax.set_ylabel("Maximum Speed Drop (%)")
        ax.grid(True)
        plt.tight_layout()
        plt.savefig("analysis/plots/load_vs_speed_drop.png", dpi=150)
        plt.close()
        print("Saved plot: analysis/plots/load_vs_speed_drop.png")

        # Plot 3: load_vs_recovery_time.png
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(torques, recs, 'bs-', linewidth=2, markersize=8)
        for t, r, m in zip(torques, recs, level_summary_metrics):
            ax.annotate(f"{m['id']}: {r:.0f}ms", (t, r), textcoords="offset points", xytext=(0, 10), ha='center')
        ax.set_title("Estimated External Torque vs Recovery Time (150 RPM)")
        ax.set_xlabel("Estimated External Torque (Nm)")
        ax.set_ylabel("Recovery Time to ±2% (ms)")
        ax.grid(True)
        plt.tight_layout()
        plt.savefig("analysis/plots/load_vs_recovery_time.png", dpi=150)
        plt.close()
        print("Saved plot: analysis/plots/load_vs_recovery_time.png")

        # Plot 4: load_vs_peak_current.png
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(torques, currs, 'mo-', linewidth=2, markersize=8)
        ax.axhline(1.50, color='r', linestyle='--', label='Safety Abort Limit (1.50 A)')
        ax.axhline(1.80, color='k', linestyle=':', label='Firmware Trip Limit (1.80 A)')
        for t, c, m in zip(torques, currs, level_summary_metrics):
            ax.annotate(f"{m['id']}: {c:.3f}A", (t, c), textcoords="offset points", xytext=(0, 10), ha='center')
        ax.set_title("Estimated External Torque vs Peak Current (150 RPM)")
        ax.set_xlabel("Estimated External Torque (Nm)")
        ax.set_ylabel("Peak Current (A)")
        ax.legend()
        ax.grid(True)
        plt.tight_layout()
        plt.savefig("analysis/plots/load_vs_peak_current.png", dpi=150)
        plt.close()
        print("Saved plot: analysis/plots/load_vs_peak_current.png")

        # Plot 5: load_vs_peak_pwm.png
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(torques, pwms, 'co-', linewidth=2, markersize=8)
        for t, p, m in zip(torques, pwms, level_summary_metrics):
            ax.annotate(f"{m['id']}: {p:.1f}%", (t, p), textcoords="offset points", xytext=(0, 10), ha='center')
        ax.set_title("Estimated External Torque vs Peak PWM Duty % (150 RPM)")
        ax.set_xlabel("Estimated External Torque (Nm)")
        ax.set_ylabel("Peak PWM Duty (%)")
        ax.grid(True)
        plt.tight_layout()
        plt.savefig("analysis/plots/load_vs_peak_pwm.png", dpi=150)
        plt.close()
        print("Saved plot: analysis/plots/load_vs_peak_pwm.png")

    except Exception as e:
        print(f"Plot generation error: {e}")

    print("\n--- PHASE 9 ENVELOPE SWEEP SUMMARY TABLE ---")
    print(f"{'Level':<6} | {'Force (N)':<10} | {'Torque (Nm)':<12} | {'Speed Drop %':<14} | {'Recovery (ms)':<14} | {'Peak Curr (A)':<14} | {'Peak PWM %':<12}")
    print("-" * 95)
    for m in level_summary_metrics:
        print(f"{m['id']:<6} | {m['force_n']:<10.2f} | {m['torque_nm']:<12.4f} | {m['drop_pct_mean']:<14.2f} | {m['rec_ms_mean']:<14.1f} | {m['peak_curr_mean']:<14.3f} | {m['peak_pwm_mean']:<12.1f}")

if __name__ == "__main__":
    run_phase9_envelope_sweep()
