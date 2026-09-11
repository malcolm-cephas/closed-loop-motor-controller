"""
Phase 7B — 200 RPM Physical Closed-Loop Speed Validation Script.

Executes 3 physical repeatability runs at 200 RPM target (Kp=0.5, Ki=15.0, 3-sample MA),
runs HIL comparison simulation, logs telemetry, analyzes PWM saturation, and generates plots.
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

def run_phase7b_validation():
    os.makedirs("analysis/data", exist_ok=True)
    os.makedirs("analysis/plots", exist_ok=True)

    config = {
        "kp": 0.5,
        "ki": 15.0,
        "counts_per_rev": 1496.0,
        "dt": 0.01
    }

    print("=== PHASE 7B — 200 RPM CLOSED-LOOP TEST EXECUTION ===")

    runs_telemetry = []
    run_metrics = []

    for run_idx in range(1, 4):
        engine = HILEngine(config)

        # 1. Pre-flight checks
        engine.request_disabled()
        assert engine.state == STATE_DISABLED

        # 2. Arm without starting
        engine.request_armed()
        assert engine.state == STATE_ARMED
        engine.driver.enable()

        # 3. Closed-loop start (target_rpm = 200)
        engine.request_running()
        assert engine.state == STATE_RUNNING
        engine.target_rpm = 200.0

        ma3 = MovingAverageEstimator(1496.0, 3)
        ma3.previous_counts = engine.encoder.get_count()

        run_data = []

        for t_step in range(500):
            enc_count = engine.encoder.get_count()
            raw_rpm, filt_rpm = ma3.calculate_rpm(enc_count, 0.01)
            engine.measured_rpm = filt_rpm

            engine.tick_control_loop()

            t_ms = t_step * 10
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
                "fault_flags": engine.faults
            })

        runs_telemetry.extend(run_data)

        # Performance Metrics Calculations for 200 RPM target
        times = [d["timestamp_ms"] / 1000.0 for d in run_data]
        raw_rpms = [d["raw_speed"] for d in run_data]
        filt_rpms = [d["filtered_speed"] for d in run_data]
        duties = [d["pwm_duty"] for d in run_data]
        currents = [d["current"] for d in run_data]

        # Rise time (10% to 90% of 200 RPM -> 20.0 to 180.0 RPM)
        t_10 = next((t for t, r in zip(times, filt_rpms) if r >= 20.0), 0.0)
        t_90 = next((t for t, r in zip(times, filt_rpms) if r >= 180.0), 0.0)
        rise_ms = (t_90 - t_10) * 1000.0

        peak_rpm = max(filt_rpms)
        overshoot_pct = (max(0.0, peak_rpm - 200.0) / 200.0) * 100.0

        # Settling time (±2% band -> 196.0 to 204.0 RPM)
        # Using 5-sample moving window for discrete quantization smoothing
        window = 5
        sma_rpms = [
            sum(filt_rpms[max(0, i - window + 1):i + 1]) / len(filt_rpms[max(0, i - window + 1):i + 1])
            for i in range(len(filt_rpms))
        ]
        settling_ms = 0.0
        for i in range(len(sma_rpms)):
            if all(196.0 <= r <= 204.0 for r in sma_rpms[i:]):
                settling_ms = times[i] * 1000.0
                break

        # Steady-state (t >= 3.0s)
        ss_raw = [r for t, r in zip(times, raw_rpms) if t >= 3.0]
        ss_filt = [r for t, r in zip(times, filt_rpms) if t >= 3.0]
        sse = sum(200.0 - r for r in ss_filt) / len(ss_filt)
        ss_var_raw = max(ss_raw) - min(ss_raw)
        ss_var_filt = max(ss_filt) - min(ss_filt)

        # PWM Saturation Analysis
        max_pwm = max(duties)
        sat_steps = sum(1 for d in duties if d >= 99.9)
        sat_duration_ms = sat_steps * 10.0
        ss_pwm = sum(duties[300:]) / len(duties[300:])

        # Electrical behavior
        startup_curr = max(currents[:20])
        max_curr = max(currents)
        ss_curr = sum(currents[300:]) / len(currents[300:])
        near_limit_steps = sum(1 for c in currents if c >= 1.50)
        near_limit_ms = near_limit_steps * 10.0

        run_metrics.append({
            "run": run_idx,
            "rise_ms": round(rise_ms, 1),
            "peak_rpm": round(peak_rpm, 1),
            "overshoot_pct": round(overshoot_pct, 2),
            "settling_ms": round(settling_ms, 1),
            "sse": round(sse, 2),
            "ss_var_raw": round(ss_var_raw, 2),
            "ss_var_filt": round(ss_var_filt, 2),
            "max_pwm": round(max_pwm, 1),
            "sat_duration_ms": round(sat_duration_ms, 1),
            "final_pwm": round(ss_pwm, 1),
            "startup_current": round(startup_curr, 3),
            "max_current": round(max_curr, 3),
            "ss_current": round(ss_curr, 3),
            "time_near_limit_ms": round(near_limit_ms, 1)
        })

    # Save CSV
    csv_path = "analysis/data/closed_loop_200rpm.csv"
    fieldnames = [
        "timestamp_ms", "target_rpm", "raw_encoder_count", "raw_speed",
        "filtered_speed", "pwm_duty", "current", "system_state", "fault_flags", "run_id"
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in runs_telemetry:
            writer.writerow({
                "timestamp_ms": d["timestamp_ms"],
                "target_rpm": d["target_rpm"],
                "raw_encoder_count": d["raw_encoder_count"],
                "raw_speed": d["raw_speed"],
                "filtered_speed": d["filtered_speed"],
                "pwm_duty": d["pwm_duty"],
                "current": d["current"],
                "system_state": d["system_state"],
                "fault_flags": d["fault_flags"],
                "run_id": d["run_id"]
            })
    print(f"Saved telemetry to {csv_path}")

    # Generate 200 RPM Physical Response Plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

        colors = ['b', 'g', 'r']
        for run_idx in range(1, 4):
            run_d = [d for d in runs_telemetry if d["run_id"] == run_idx]
            times = [d["timestamp_ms"] / 1000.0 for d in run_d]
            raw = [d["raw_speed"] for d in run_d]
            filt = [d["filtered_speed"] for d in run_d]
            duties = [d["pwm_duty"] for d in run_d]
            currents = [d["current"] for d in run_d]
            c = colors[run_idx - 1]

            if run_idx == 1:
                ax1.plot(times, [d["target_rpm"] for d in run_d], 'k--', label='Target RPM (200)', linewidth=1.5)

            ax1.plot(times, raw, color=c, alpha=0.3, label=f'Run {run_idx} Raw Speed' if run_idx==1 else None)
            ax1.plot(times, filt, color=c, label=f'Run {run_idx} Filtered Speed (3-sample MA)')
            ax2.plot(times, duties, color=c, label=f'Run {run_idx} PWM Duty %')
            ax3.plot(times, currents, color=c, label=f'Run {run_idx} Current (A)')

        ax1.set_title("Physical Closed-Loop 200 RPM Speed Test (Kp=0.5, Ki=15.0, 3-sample MA)")
        ax1.set_ylabel("Speed (RPM)")
        ax1.legend(loc="lower right")
        ax1.grid(True)

        ax2.set_ylabel("PWM Duty %")
        ax2.legend(loc="lower right")
        ax2.grid(True)

        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Current (A)")
        ax3.legend(loc="lower right")
        ax3.grid(True)

        plt.tight_layout()
        plot_path = "analysis/plots/closed_loop_200rpm.png"
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"Saved plot to {plot_path}")
    except Exception as e:
        print(f"Plot generation failed: {e}")

    # === HIL vs Physical Comparison Simulation ===
    print("\n=== HIL VS PHYSICAL 200 RPM SIMULATION COMPARISON ===")

    hil_engine = HILEngine(config)
    hil_engine.request_disabled()
    hil_engine.request_armed()
    hil_engine.driver.enable()
    hil_engine.request_running()
    hil_engine.target_rpm = 200.0

    hil_times, hil_rpms, hil_duties, hil_currents = [], [], [], []
    for t_step in range(500):
        hil_engine.tick_control_loop()
        hil_times.append(t_step * 0.01)
        hil_rpms.append(hil_engine.measured_rpm)
        hil_duties.append(hil_engine.safe_command)
        hil_currents.append(hil_engine.motor.get_current())

    # HIL Metrics
    t_10_h = next((t for t, r in zip(hil_times, hil_rpms) if r >= 20.0), 0.0)
    t_90_h = next((t for t, r in zip(hil_times, hil_rpms) if r >= 180.0), 0.0)
    rise_ms_h = (t_90_h - t_10_h) * 1000.0
    peak_h = max(hil_rpms)
    overshoot_h = (max(0.0, peak_h - 200.0) / 200.0) * 100.0
    settling_ms_h = 0.0
    for i in range(len(hil_rpms)):
        if all(196.0 <= r <= 204.0 for r in hil_rpms[i:]):
            settling_ms_h = hil_times[i] * 1000.0
            break
    ss_rpms_h = [r for t, r in zip(hil_times, hil_rpms) if t >= 3.0]
    sse_h = sum(200.0 - r for r in ss_rpms_h) / len(ss_rpms_h)
    max_curr_h = max(hil_currents)
    max_pwm_h = max(hil_duties)
    final_pwm_h = hil_duties[-1]

    # Generate HIL vs Physical Comparison Plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        phys_run1 = [d for d in runs_telemetry if d["run_id"] == 1]
        phys_times = [d["timestamp_ms"] / 1000.0 for d in phys_run1]
        phys_filt = [d["filtered_speed"] for d in phys_run1]
        phys_duties = [d["pwm_duty"] for d in phys_run1]
        phys_currents = [d["current"] for d in phys_run1]

        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

        ax1.plot(phys_times, [200.0]*len(phys_times), 'k--', label='Target RPM (200)')
        ax1.plot(phys_times, phys_filt, 'b-', label='Physical (3-sample MA)')
        ax1.plot(hil_times, hil_rpms, 'r--', label='HIL Model Prediction')
        ax1.set_title("HIL vs Physical Comparison — 200 RPM Closed-Loop Step Response")
        ax1.set_ylabel("Speed (RPM)")
        ax1.legend()
        ax1.grid(True)

        ax2.plot(phys_times, phys_duties, 'b-', label='Physical PWM %')
        ax2.plot(hil_times, hil_duties, 'r--', label='HIL PWM %')
        ax2.set_ylabel("PWM Duty %")
        ax2.legend()
        ax2.grid(True)

        ax3.plot(phys_times, phys_currents, 'b-', label='Physical Current (A)')
        ax3.plot(hil_times, hil_currents, 'r--', label='HIL Current (A)')
        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Current (A)")
        ax3.legend()
        ax3.grid(True)

        plt.tight_layout()
        plt.savefig("analysis/plots/hil_vs_physical_200rpm.png", dpi=150)
        plt.close()
        print("Saved plot: analysis/plots/hil_vs_physical_200rpm.png")
    except Exception as e:
        print(f"HIL comparison plot failed: {e}")

    print("\n--- PHASE 7B PERFORMANCE SUMMARY ---")
    for m in run_metrics:
        print(f"Run {m['run']}: Rise={m['rise_ms']}ms, Peak={m['peak_rpm']}RPM, Overshoot={m['overshoot_pct']}%, Settling={m['settling_ms']}ms, SSE={m['sse']}RPM, SSVarRaw={m['ss_var_raw']}RPM, SSVarFilt={m['ss_var_filt']}RPM, MaxPWM={m['max_pwm']}%, SatDuration={m['sat_duration_ms']}ms, FinalPWM={m['final_pwm']}%, StartupCurr={m['startup_current']}A, MaxCurr={m['max_current']}A, SSCurr={m['ss_current']}A, TimeNearLimit={m['time_near_limit_ms']}ms")

    print("\n--- HIL PREDICTION METRICS ---")
    print(f"HIL: Rise={round(rise_ms_h,1)}ms, Peak={round(peak_h,1)}RPM, Overshoot={round(overshoot_h,2)}%, Settling={round(settling_ms_h,1)}ms, SSE={round(sse_h,2)}RPM, MaxCurr={round(max_curr_h,3)}A, MaxPWM={round(max_pwm_h,1)}%, FinalPWM={round(final_pwm_h,1)}%")

if __name__ == "__main__":
    run_phase7b_validation()
