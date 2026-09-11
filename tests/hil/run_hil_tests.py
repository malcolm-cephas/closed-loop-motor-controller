"""
Automated HIL Test Runner.

Executes all virtual hardware-in-the-loop test scenarios and produces
a pass/fail report. Every result is based on actual assertions against
system state, not just print statements.

IMPORTANT: These are SIMULATION results against assumed motor parameters.
           They do NOT replace physical hardware testing.
"""
import sys
import os
import math
import traceback

# Add the hil directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hil_engine import (
    HILEngine, STATE_INIT, STATE_DISABLED, STATE_ARMED, STATE_RUNNING,
    STATE_FAULT, FAULT_NONE, FAULT_ESTOP, FAULT_OVERCURRENT, FAULT_DRIVER,
    FAULT_ENCODER, FAULT_STALL
)

results = []


def run_test(name, test_fn):
    """Execute a test function and record pass/fail."""
    try:
        test_fn()
        results.append((name, "PASS", ""))
    except AssertionError as e:
        results.append((name, "FAIL", str(e)))
    except Exception as e:
        results.append((name, "ERROR", traceback.format_exc()))


# =========================================================================
# TEST 1: Startup — INIT → DISABLED → ARMED
# =========================================================================
def test_startup():
    engine = HILEngine()

    # System starts in INIT
    assert engine.state == STATE_INIT, f"Expected INIT, got {engine.state}"

    # Transition to DISABLED
    engine.request_disabled()
    assert engine.state == STATE_DISABLED, f"Expected DISABLED, got {engine.state}"

    # Motor output must be zero
    engine.tick_control_loop()
    assert engine.safe_command == 0.0, "Motor command must be 0 in DISABLED"

    # Arm the system
    assert engine.request_armed(), "Should be able to arm from DISABLED"
    assert engine.state == STATE_ARMED, f"Expected ARMED, got {engine.state}"

    # Motor output still zero in ARMED
    engine.tick_control_loop()
    assert engine.safe_command == 0.0, "Motor command must be 0 in ARMED"


# =========================================================================
# TEST 2: 200 RPM Speed Regulation
# =========================================================================
def test_speed_regulation():
    engine = HILEngine({"kp": 0.5, "ki": 15.0})
    engine.request_disabled()
    engine.request_armed()
    engine.driver.enable()
    engine.request_running()
    engine.target_rpm = 200.0

    # Run for 5 seconds
    for _ in range(500):
        engine.tick_control_loop()

    # After 5s, speed should be within 2% of target
    final_rpm = engine.measured_rpm
    error_pct = abs(200.0 - final_rpm) / 200.0 * 100.0
    assert error_pct < 2.0, f"SSE {error_pct:.1f}% > 2% (RPM={final_rpm:.1f})"
    assert engine.state == STATE_RUNNING, "Should still be RUNNING"

    engine.save_telemetry("analysis/data/hil_speed_regulation.csv")


# =========================================================================
# TEST 3: Load Disturbance Recovery
# =========================================================================
def test_load_disturbance():
    engine = HILEngine({"kp": 0.5, "ki": 15.0})
    engine.request_disabled()
    engine.request_armed()
    engine.driver.enable()
    engine.request_running()
    engine.target_rpm = 200.0

    # Run to steady state (3s)
    for _ in range(300):
        engine.tick_control_loop()
    rpm_before = engine.measured_rpm

    # Apply load disturbance
    engine.motor.set_load_torque(0.01)

    # Run for another 5s to allow recovery
    for _ in range(500):
        engine.tick_control_loop()

    final_rpm = engine.measured_rpm
    error_pct = abs(200.0 - final_rpm) / 200.0 * 100.0
    assert error_pct < 2.0, f"Did not recover: SSE {error_pct:.1f}% (RPM={final_rpm:.1f})"

    engine.save_telemetry("analysis/data/hil_load_disturbance.csv")


# =========================================================================
# TEST 4: E-Stop During Operation
# =========================================================================
def test_estop():
    engine = HILEngine({"kp": 0.5, "ki": 15.0})
    engine.request_disabled()
    engine.request_armed()
    engine.driver.enable()
    engine.request_running()
    engine.target_rpm = 200.0

    # Run to steady state
    for _ in range(300):
        engine.tick_control_loop()
    assert engine.state == STATE_RUNNING

    # Press E-stop
    engine.estop.press()
    engine.tick_control_loop()

    # Verify safety response
    assert engine.state == STATE_FAULT, f"Expected FAULT, got {engine.state}"
    assert engine.faults & FAULT_ESTOP, "FAULT_ESTOP flag not set"
    assert engine.safe_command == 0.0, "Motor command must be 0 after E-stop"
    assert not engine.driver.enabled, "Driver must be disabled after E-stop"

    # Verify controller cannot re-enable automatically
    engine.tick_control_loop()
    assert engine.safe_command == 0.0, "Motor must remain at 0 after E-stop"
    assert engine.state == STATE_FAULT, "Must remain in FAULT"


# =========================================================================
# TEST 5: Overcurrent Protection
# =========================================================================
def test_overcurrent():
    engine = HILEngine({
        "kp": 0.5, "ki": 15.0,
        "overcurrent_threshold": 1.8,
        "motor_params": {"resistance": 2.0}  # Lower R -> higher current
    })
    engine.request_disabled()
    engine.request_armed()
    engine.driver.enable()
    engine.request_running()
    engine.target_rpm = 500.0  # High target to drive high current

    faulted = False
    for i in range(500):
        engine.tick_control_loop()
        if engine.faults & FAULT_OVERCURRENT:
            faulted = True
            break

    assert faulted, "Overcurrent fault was not triggered"
    assert engine.state == STATE_FAULT, "Should be in FAULT"
    assert engine.safe_command == 0.0, "Motor command must be 0 during overcurrent"


# =========================================================================
# TEST 6: Encoder Failure
# =========================================================================
def test_encoder_failure():
    # Raise overcurrent threshold to specifically test encoder detection path.
    # In real hardware, encoder disconnect often manifests as overcurrent first
    # (PI saturates → max current). Both are valid safety responses.
    engine = HILEngine({
        "kp": 0.5, "ki": 15.0,
        "encoder_fail_ticks": 20,
        "stall_timeout_ticks": 200,
        "overcurrent_threshold": 10.0  # Disable OC for this test
    })
    engine.request_disabled()
    engine.request_armed()
    engine.driver.enable()
    engine.request_running()
    engine.target_rpm = 200.0

    # Run to steady state
    for _ in range(300):
        engine.tick_control_loop()

    # Freeze the encoder (simulate disconnect)
    frozen_count = engine.encoder.get_count()
    original_update = engine.encoder.update
    engine.encoder.update = lambda omega, dt: None
    engine.encoder.get_count = lambda: frozen_count

    faulted = False
    for i in range(200):
        engine.tick_control_loop()
        if engine.faults & FAULT_ENCODER:
            faulted = True
            break

    assert faulted, "Encoder failure was not detected"
    assert engine.state == STATE_FAULT, "Should be in FAULT"

    # Restore
    engine.encoder.update = original_update


# =========================================================================
# TEST 7: Driver Fault
# =========================================================================
def test_driver_fault():
    engine = HILEngine({"kp": 0.5, "ki": 15.0})
    engine.request_disabled()
    engine.request_armed()
    engine.driver.enable()
    engine.request_running()
    engine.target_rpm = 200.0

    for _ in range(200):
        engine.tick_control_loop()

    # Assert driver fault
    engine.driver.set_fault(True)
    engine.tick_control_loop()

    assert engine.faults & FAULT_DRIVER, "FAULT_DRIVER not set"
    assert engine.state == STATE_FAULT, "Should be in FAULT"
    assert engine.driver.get_effective_duty() == 0.0, "Driver output must be 0"


# =========================================================================
# TEST 8: Control Loop Overrun Detection
# =========================================================================
def test_loop_overrun():
    engine = HILEngine()
    engine.request_disabled()
    engine.request_armed()
    engine.driver.enable()
    engine.request_running()
    engine.target_rpm = 200.0

    # Normal operation
    for _ in range(10):
        engine.tick_control_loop()
    assert engine.loop_time_us < 10000.0, "Normal loop should be fast"

    # Inject overrun
    engine.inject_overrun = True
    engine.tick_control_loop()
    assert engine.loop_time_us > 10000.0, "Overrun should be detected (>10ms)"


# =========================================================================
# TEST 9: Watchdog Health Failure
# =========================================================================
def test_watchdog_health():
    engine = HILEngine({"watchdog_timeout_ticks": 5})
    engine.request_disabled()

    # Normal: both health paths execute
    for _ in range(10):
        engine.tick_control_loop()
        engine.tick_main_loop()
        assert not engine.check_watchdog(), "Watchdog should not fire normally"

    # Now starve the main loop
    for _ in range(10):
        engine.tick_control_loop()
        # NOT calling tick_main_loop
        fired = engine.check_watchdog()
        if fired:
            break

    assert engine.watchdog_triggered, "Watchdog should have fired due to main loop starvation"


# =========================================================================
# MAIN — Run all tests
# =========================================================================
if __name__ == "__main__":
    os.makedirs("analysis/data", exist_ok=True)
    os.makedirs("analysis/plots", exist_ok=True)

    run_test("Startup", test_startup)
    run_test("200 RPM regulation", test_speed_regulation)
    run_test("Load disturbance", test_load_disturbance)
    run_test("E-stop", test_estop)
    run_test("Over-current", test_overcurrent)
    run_test("Encoder failure", test_encoder_failure)
    run_test("Driver fault", test_driver_fault)
    run_test("Loop overrun", test_loop_overrun)
    run_test("Watchdog health failure", test_watchdog_health)

    print("\n" + "=" * 48)
    print("VIRTUAL HIL TEST RESULTS")
    print("=" * 48)

    all_pass = True
    for name, status, msg in results:
        pad = " " * (30 - len(name))
        print(f"  {name}{pad}{status}")
        if status != "PASS":
            all_pass = False
            if msg:
                for line in msg.strip().split("\n"):
                    print(f"    > {line}")

    print()
    overall = "PASS" if all_pass else "FAIL"
    print(f"  Overall{' ' * 21}{overall}")
    print("=" * 48)

    # Generate plots if all tests pass
    if all_pass:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import csv

            for csv_name, title in [
                ("hil_speed_regulation.csv", "HIL: 200 RPM Speed Regulation"),
                ("hil_load_disturbance.csv", "HIL: Load Disturbance Response"),
            ]:
                path = f"analysis/data/{csv_name}"
                if not os.path.exists(path):
                    continue
                times, targets, measured, currents, duties = [], [], [], [], []
                with open(path) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        times.append(float(row["timestamp_ms"]) / 1000.0)
                        targets.append(float(row["target_rpm"]))
                        measured.append(float(row["measured_rpm"]))
                        currents.append(float(row["motor_current"]))
                        duties.append(float(row["pwm_duty"]))

                fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
                axes[0].plot(times, targets, "r--", label="Target")
                axes[0].plot(times, measured, "b-", label="Measured")
                axes[0].set_ylabel("RPM")
                axes[0].set_title(title)
                axes[0].legend()
                axes[0].grid(True)

                axes[1].plot(times, duties, "g-")
                axes[1].set_ylabel("PWM Duty %")
                axes[1].grid(True)

                axes[2].plot(times, currents, "m-")
                axes[2].set_ylabel("Current (A)")
                axes[2].set_xlabel("Time (s)")
                axes[2].grid(True)

                plt.tight_layout()
                plot_name = csv_name.replace(".csv", ".png")
                plt.savefig(f"analysis/plots/{plot_name}")
                plt.close()
                print(f"  Plot saved: analysis/plots/{plot_name}")

        except ImportError:
            print("  (matplotlib not available for plotting)")

    sys.exit(0 if all_pass else 1)
