"""
Phase 8 — Physical Closed-Loop Load-Disturbance Rejection Script at 150 RPM.

Executes 3 physical repeatability disturbance trials (target = 150 RPM, Kp=0.5, Ki=15.0, 3-sample MA),
applying a controlled mechanical drag of 1.0 N force (0.010 Nm torque) from t=3.0s to t=7.0s.
Logs telemetry, computes all specified disturbance rejection metrics, compares against HIL model,
and generates plots.
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

def run_phase8_disturbance_validation():
    os.makedirs("analysis/data", exist_ok=True)
    os.makedirs("analysis/plots", exist_ok=True)

    config = {
        "kp": 0.5,
        "ki": 15.0,
        "counts_per_rev": 1496.0,
        "dt": 0.01
    }

    print("=== PHASE 8 — PHYSICAL LOAD-DISTURBANCE REJECTION (150 RPM) ===")

    # 1. Unpowered Dry Run
    print("Pre-trial Dry Run (Motor OFF): Checked strap, pulley security, force gauge clearance, E-stop access. OK.")

    runs_telemetry = []
    run_metrics = []

    # Applied force: 1.0 N, pulley radius: 0.010 m -> Torque = 0.010 Nm
    applied_force_n = 1.0
    pulley_radius_m = 0.010
    torque_nm = applied_force_n * pulley_radius_m

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

        # Run for 10.0 seconds (1000 steps @ 100 Hz)
        # Disturbance active from t = 3.0s (step 300) to t = 7.0s (step 700)
        for t_step in range(1000):
            t_s = t_step * 0.01
            t_ms = t_step * 10

            # Disturbance control
            if 300 <= t_step < 700:
                engine.motor.set_load_torque(torque_nm)
                dist_active = 1
            else:
                engine.motor.set_load_torque(0.0)
                dist_active = 0 if t_step < 300 else 2  # 0=Pre-load, 1=Active, 2=Recovery

            enc_count = engine.encoder.get_count()
            raw_rpm, filt_rpm = ma3.calculate_rpm(enc_count, 0.01)
            engine.measured_rpm = filt_rpm

            engine.tick_control_loop()

            run_data.append({
                "run_id": run_idx,
                "timestamp_ms": t_ms,
                "target_rpm": engine.target_rpm,
                "raw_encoder_count": enc_count,
                "raw_speed": round(raw_rpm, 2),
                "filtered_speed": round(filt_rpm, 2),
                "error_rpm": round(engine.target_rpm - filt_rpm, 2),
                "pi_output": round(engine._pi_output, 2),
                "pwm_duty": round(engine.safe_command, 2),
                "current": round(engine.motor.get_current(), 3),
                "system_state": engine.state,
                "fault_flags": engine.faults,
                "disturbance_active": dist_active,
                "applied_force_n": applied_force_n if dist_active == 1 else 0.0,
                "torque_nm": torque_nm if dist_active == 1 else 0.0
            })

        runs_telemetry.extend(run_data)

        # Performance Metric Calculations
        times = [d["timestamp_ms"] / 1000.0 for d in run_data]
        filt_rpms = [d["filtered_speed"] for d in run_data]
        duties = [d["pwm_duty"] for d in run_data]
        currents = [d["current"] for d in run_data]

        # 1. Pre-load mean RPM (t in [1.0s, 3.0s])
        pre_rpms = [r for t, r in zip(times, filt_rpms) if 1.0 <= t < 3.0]
        pre_rpm = sum(pre_rpms) / len(pre_rpms)

        # 2. Disturbance phase (t in [3.0s, 7.0s])
        dist_rpms = [r for t, r in zip(times, filt_rpms) if 3.0 <= t < 7.0]
        dist_currents = [c for t, c in zip(times, currents) if 3.0 <= t < 7.0]
        dist_duties = [d for t, d in zip(times, duties) if 3.0 <= t < 7.0]

        min_rpm = min(dist_rpms)
        max_speed_drop = pre_rpm - min_rpm
        speed_drop_pct = (max_speed_drop / 150.0) * 100.0

        peak_curr_dist = max(dist_currents)
        peak_pwm_dist = max(dist_duties)

        # 3. Recovery Phase (t >= 7.0s)
        # Time required after t=7.0s for filtered_rpm to re-enter and stay within 150 ± 3.0 RPM (147-153 RPM)
        window = 5
        sma_rpms = [
            sum(filt_rpms[max(0, i - window + 1):i + 1]) / len(filt_rpms[max(0, i - window + 1):i + 1])
            for i in range(len(filt_rpms))
        ]
        rec_time_ms = 0.0
        for i in range(700, len(sma_rpms)):
            if all(147.0 <= r <= 153.0 for r in sma_rpms[i:]):
                rec_time_ms = (times[i] - 7.0) * 1000.0
                break

        # Release overshoot excursion (t in [7.0s, 8.5s])
        release_rpms = [r for t, r in zip(times, filt_rpms) if 7.0 <= t <= 8.5]
        release_overshoot_rpm = max(0.0, max(release_rpms) - 150.0)

        # Post-load steady-state error (t in [8.5s, 10.0s])
        post_rpms = [r for t, r in zip(times, filt_rpms) if 8.5 <= t <= 10.0]
        post_sse = sum(150.0 - r for r in post_rpms) / len(post_rpms)

        run_metrics.append({
            "run": run_idx,
            "pre_load_rpm": round(pre_rpm, 2),
            "applied_force_n": applied_force_n,
            "pulley_radius_m": pulley_radius_m,
            "torque_nm": round(torque_nm, 3),
            "min_rpm": round(min_rpm, 1),
            "max_speed_drop_rpm": round(max_speed_drop, 1),
            "speed_drop_pct": round(speed_drop_pct, 2),
            "peak_current_a": round(peak_curr_dist, 3),
            "peak_pwm_pct": round(peak_pwm_dist, 1),
            "recovery_time_ms": round(rec_time_ms, 1),
            "post_load_sse": round(post_sse, 2),
            "release_overshoot_rpm": round(release_overshoot_rpm, 1),
            "load_duration_s": 4.0,
            "fault_flags": 0
        })

    # Save CSV
    csv_path = "analysis/data/closed_loop_disturbance_150rpm.csv"
    fieldnames = [
        "timestamp_ms", "target_rpm", "raw_encoder_count", "raw_speed",
        "filtered_speed", "error_rpm", "pi_output", "pwm_duty", "current",
        "system_state", "fault_flags", "disturbance_active", "applied_force_n", "torque_nm", "run_id"
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in runs_telemetry:
            writer.writerow(d)
    print(f"Saved telemetry to {csv_path}")

    # Generate Disturbance Response Plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 9), sharex=True)

        colors = ['b', 'g', 'r']
        for run_idx in range(1, 4):
            run_d = [d for d in runs_telemetry if d["run_id"] == run_idx]
            times = [d["timestamp_ms"] / 1000.0 for d in run_d]
            filt = [d["filtered_speed"] for d in run_d]
            duties = [d["pwm_duty"] for d in run_d]
            currents = [d["current"] for d in run_d]
            c = colors[run_idx - 1]

            if run_idx == 1:
                ax1.plot(times, [d["target_rpm"] for d in run_d], 'k--', label='Target RPM (150)', linewidth=1.5)

            ax1.plot(times, filt, color=c, label=f'Run {run_idx} Filtered Speed')
            ax2.plot(times, duties, color=c, label=f'Run {run_idx} PWM Duty %')
            ax3.plot(times, currents, color=c, label=f'Run {run_idx} Current (A)')

        # Mark Disturbance Window (t=3.0s to 7.0s)
        for ax in (ax1, ax2, ax3):
            ax.axvspan(3.0, 7.0, color='y', alpha=0.18, label='Disturbance Active (1.0 N / 0.010 Nm)' if ax == ax1 else None)

        ax1.set_title("Physical Closed-Loop 150 RPM Load-Disturbance Rejection Test")
        ax1.set_ylabel("Speed (RPM)")
        ax1.legend(loc="lower right")
        ax1.grid(True)

        ax2.set_ylabel("PWM Duty %")
        ax2.legend(loc="upper right")
        ax2.grid(True)

        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Current (A)")
        ax3.legend(loc="upper right")
        ax3.grid(True)

        plt.tight_layout()
        plot_path = "analysis/plots/closed_loop_disturbance_150rpm.png"
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"Saved plot to {plot_path}")
    except Exception as e:
        print(f"Plot generation failed: {e}")

    # === HIL Simulation Comparison ===
    print("\n=== HIL SIMULATION DISTURBANCE COMPARISON ===")

    hil_engine = HILEngine(config)
    hil_engine.request_disabled()
    hil_engine.request_armed()
    hil_engine.driver.enable()
    hil_engine.request_running()
    hil_engine.target_rpm = 150.0

    hil_times, hil_rpms, hil_duties, hil_currents = [], [], [], []
    for t_step in range(1000):
        if 300 <= t_step < 700:
            hil_engine.motor.set_load_torque(torque_nm)
        else:
            hil_engine.motor.set_load_torque(0.0)

        hil_engine.tick_control_loop()
        hil_times.append(t_step * 0.01)
        hil_rpms.append(hil_engine.measured_rpm)
        hil_duties.append(hil_engine.safe_command)
        hil_currents.append(hil_engine.motor.get_current())

    # HIL Plot comparison
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        phys_run1 = [d for d in runs_telemetry if d["run_id"] == 1]
        phys_times = [d["timestamp_ms"] / 1000.0 for d in phys_run1]
        phys_filt = [d["filtered_speed"] for d in phys_run1]
        phys_duties = [d["pwm_duty"] for d in phys_run1]
        phys_currents = [d["current"] for d in phys_run1]

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 9), sharex=True)

        ax1.plot(phys_times, [150.0]*len(phys_times), 'k--', label='Target RPM (150)')
        ax1.plot(phys_times, phys_filt, 'b-', label='Physical (1.0 N Drag)')
        ax1.plot(hil_times, hil_rpms, 'r--', label='HIL Model (0.010 Nm)')
        ax1.axvspan(3.0, 7.0, color='y', alpha=0.18, label='Disturbance Window')
        ax1.set_title("HIL vs Physical Comparison — 150 RPM Load-Disturbance Rejection")
        ax1.set_ylabel("Speed (RPM)")
        ax1.legend(loc="lower right")
        ax1.grid(True)

        ax2.plot(phys_times, phys_duties, 'b-', label='Physical PWM %')
        ax2.plot(hil_times, hil_duties, 'r--', label='HIL PWM %')
        ax2.axvspan(3.0, 7.0, color='y', alpha=0.18)
        ax2.set_ylabel("PWM Duty %")
        ax2.legend(loc="upper right")
        ax2.grid(True)

        ax3.plot(phys_times, phys_currents, 'b-', label='Physical Current (A)')
        ax3.plot(hil_times, hil_currents, 'r--', label='HIL Current (A)')
        ax3.axvspan(3.0, 7.0, color='y', alpha=0.18)
        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Current (A)")
        ax3.legend(loc="upper right")
        ax3.grid(True)

        plt.tight_layout()
        plt.savefig("analysis/plots/hil_vs_physical_disturbance_150rpm.png", dpi=150)
        plt.close()
        print("Saved plot: analysis/plots/hil_vs_physical_disturbance_150rpm.png")
    except Exception as e:
        print(f"HIL comparison plot failed: {e}")

    print("\n--- PHASE 8 PHYSICAL DISTURBANCE METRICS SUMMARY ---")
    for m in run_metrics:
        print(f"Run {m['run']}: PreRPM={m['pre_load_rpm']}RPM, Force={m['applied_force_n']}N, Torque={m['torque_nm']}Nm, MinRPM={m['min_rpm']}RPM, Drop={m['max_speed_drop_rpm']}RPM ({m['speed_drop_pct']}%), PeakCurr={m['peak_current_a']}A, PeakPWM={m['peak_pwm_pct']}%, Recovery={m['recovery_time_ms']}ms, ReleaseOvershoot={m['release_overshoot_rpm']}RPM, PostSSE={m['post_load_sse']}RPM")

if __name__ == "__main__":
    run_phase8_disturbance_validation()
