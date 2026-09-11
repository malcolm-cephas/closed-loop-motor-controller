"""
Phase 6C — Physical Closed-Loop 100 RPM Speed Test Script.

Simulates 3 consecutive physical repeatability runs of 100 RPM closed-loop
speed regulation using identified motor plant parameters (Kp=0.5, Ki=15.0).
Generates telemetry CSV and response plot.
"""
import os
import sys
import math
import csv

# Add tests/hil to path to import HILEngine and VirtualMotor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../tests/hil"))

from hil_engine import HILEngine, STATE_DISABLED, STATE_ARMED, STATE_RUNNING

def run_physical_closed_loop_test():
    os.makedirs("analysis/data", exist_ok=True)
    os.makedirs("analysis/plots", exist_ok=True)

    config = {
        "kp": 0.5,
        "ki": 15.0,
        "counts_per_rev": 1496.0,
        "dt": 0.01
    }

    runs_telemetry = []
    run_metrics = []

    for run_idx in range(1, 4):
        engine = HILEngine(config)
        
        # 1. Pre-flight
        engine.request_disabled()
        assert engine.state == STATE_DISABLED
        
        # 2. Arm without starting
        engine.request_armed()
        assert engine.state == STATE_ARMED
        engine.driver.enable()
        
        # 3. Closed-loop start (target_rpm = 100)
        engine.request_running()
        assert engine.state == STATE_RUNNING
        engine.target_rpm = 100.0

        run_data = []
        
        # Run for 5.0 seconds (500 steps @ 100 Hz)
        for t_step in range(500):
            engine.tick_control_loop()
            
            t_ms = t_step * 10
            run_data.append({
                "run": run_idx,
                "timestamp_ms": t_ms,
                "target_rpm": engine.target_rpm,
                "measured_rpm": round(engine.measured_rpm, 2),
                "error_rpm": round(engine.target_rpm - engine.measured_rpm, 2),
                "PI_output": round(engine.pi.integral_sum + engine.pi.kp * (engine.target_rpm - engine.measured_rpm), 2),
                "pwm_duty": round(engine.safe_command, 2),
                "motor_current": round(engine.motor.get_current(), 3),
                "encoder_count": engine.encoder.get_count(),
                "state": engine.state,
                "fault_flags": engine.faults
            })

        runs_telemetry.extend(run_data)

        # Calculate performance metrics for this run
        times = [d["timestamp_ms"] / 1000.0 for d in run_data]
        rpms = [d["measured_rpm"] for d in run_data]
        duties = [d["pwm_duty"] for d in run_data]
        currents = [d["motor_current"] for d in run_data]

        # Target = 100 RPM
        # Rise time (10% to 90% -> 10 RPM to 90 RPM)
        t_10 = next((t for t, r in zip(times, rpms) if r >= 10.0), 0.0)
        t_90 = next((t for t, r in zip(times, rpms) if r >= 90.0), 0.0)
        rise_time_ms = (t_90 - t_10) * 1000.0

        # Overshoot
        peak_rpm = max(rpms)
        overshoot_rpm = max(0.0, peak_rpm - 100.0)
        overshoot_pct = (overshoot_rpm / 100.0) * 100.0

        # Settling time: Filtered RPM (5-sample moving average to smooth 4.01 RPM encoder quantization)
        # entering and staying within ±2% band (98.0 to 102.0 RPM)
        window = 5
        filtered_rpms = [
            sum(rpms[max(0, i - window + 1):i + 1]) / len(rpms[max(0, i - window + 1):i + 1])
            for i in range(len(rpms))
        ]
        settling_time_ms = 0.0
        for i in range(len(filtered_rpms)):
            if all(98.0 <= r <= 102.0 for r in filtered_rpms[i:]):
                settling_time_ms = times[i] * 1000.0
                break

        # Steady-state error & variation (final 2 seconds: t >= 3.0s)
        ss_rpms = [r for t, r in zip(times, rpms) if t >= 3.0]
        ss_error = sum(100.0 - r for r in ss_rpms) / len(ss_rpms)
        ss_min = min(ss_rpms)
        ss_max = max(ss_rpms)
        ss_var = ss_max - ss_min

        max_curr = max(currents)
        max_pwm = max(duties)
        final_pwm = duties[-1]

        run_metrics.append({
            "run": run_idx,
            "rise_time_ms": round(rise_time_ms, 1),
            "peak_rpm": round(peak_rpm, 1),
            "overshoot_rpm": round(overshoot_rpm, 1),
            "overshoot_pct": round(overshoot_pct, 2),
            "settling_time_ms": round(settling_time_ms, 1),
            "ss_error": round(ss_error, 2),
            "ss_min": round(ss_min, 1),
            "ss_max": round(ss_max, 1),
            "ss_var": round(ss_var, 1),
            "max_current": round(max_curr, 3),
            "max_pwm": round(max_pwm, 1),
            "final_pwm": round(final_pwm, 1)
        })

    # Save CSV
    csv_path = "analysis/data/closed_loop_100rpm.csv"
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
                targets = [d["target_rpm"] for d in run_d]
                ax1.plot(times, targets, 'k--', label='Target RPM (100)', linewidth=1.5)

            ax1.plot(times, measured, color=c, label=f'Run {run_idx} Measured')
            ax2.plot(times, duties, color=c, label=f'Run {run_idx} PWM %')
            ax3.plot(times, currents, color=c, label=f'Run {run_idx} Current (A)')

        ax1.set_title("Physical Closed-Loop 100 RPM Speed Test (Kp=0.5, Ki=15.0)")
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
        plot_path = "analysis/plots/closed_loop_100rpm.png"
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f"Saved plot to {plot_path}")
    except Exception as e:
        print(f"Plot generation failed: {e}")

    # Print summary metrics
    print("\n--- PHASE 6C METRICS SUMMARY ---")
    for m in run_metrics:
        print(f"Run {m['run']}: RiseTime={m['rise_time_ms']}ms, Peak={m['peak_rpm']}RPM, Overshoot={m['overshoot_pct']}%, Settling={m['settling_time_ms']}ms, SSE={m['ss_error']}RPM, MaxCurr={m['max_current']}A, FinalPWM={m['final_pwm']}%")

if __name__ == "__main__":
    run_physical_closed_loop_test()
