"""
VitalSense Demo Simulator — based on the ESP32 hardware sketch logic.

Mirrors the exact same thresholds used on the real device:
  EMERGENCY (RED)    : temp > 40  OR  heartRate > 150  OR  fallDetected
  WARNING   (YELLOW) : temp > 38  OR  heartRate > 120
  NORMAL    (GREEN)  : everything else

Runs four demo patients:
  DEMO-1  permanently NORMAL    (GREEN)
  DEMO-2  permanently WARNING   (YELLOW)
  DEMO-3  permanently EMERGENCY (RED)
  DEMO-4  cycles through all three states (~15 s each)

Usage:
  python demo_simulator.py              # all four patients
  python demo_simulator.py --interval 1 # slower rate
"""

import argparse
import json
import math
import random
import time
import paho.mqtt.client as mqtt
import config

# ── Scenario generators ────────────────────────────────────────────────────────

def _normal_vitals(patient_id):
    """Green zone: HR ≤ 120, temp ≤ 38, no fall."""
    return {
        "patient_id":  patient_id,
        "heart_rate":  round(random.uniform(65, 90), 1),
        "spo2":        round(random.uniform(96, 100), 1),
        "temperature": round(random.uniform(36.5, 37.8), 2),
        "movement":    round(random.uniform(0.0, 0.15), 3),
    }

def _warning_vitals(patient_id):
    """Yellow zone: HR 121-149 OR temp 38.1-39.9."""
    # Alternate between high HR and high temp
    if random.random() < 0.5:
        hr   = round(random.uniform(121, 149), 1)
        temp = round(random.uniform(36.5, 37.9), 2)
    else:
        hr   = round(random.uniform(80, 110), 1)
        temp = round(random.uniform(38.1, 39.9), 2)
    return {
        "patient_id":  patient_id,
        "heart_rate":  hr,
        "spo2":        round(random.uniform(90, 95), 1),
        "temperature": temp,
        "movement":    round(random.uniform(0.1, 0.4), 3),
    }

def _emergency_vitals(patient_id, trigger="hr"):
    """Red zone: temp > 40 OR HR > 150 OR fall (high movement)."""
    if trigger == "hr":
        hr   = round(random.uniform(151, 180), 1)
        temp = round(random.uniform(37.0, 39.0), 2)
        mov  = round(random.uniform(0.2, 0.5), 3)
    elif trigger == "temp":
        hr   = round(random.uniform(100, 140), 1)
        temp = round(random.uniform(40.1, 41.5), 2)
        mov  = round(random.uniform(0.2, 0.5), 3)
    else:                              # fall
        hr   = round(random.uniform(90, 130), 1)
        temp = round(random.uniform(36.5, 38.5), 2)
        mov  = round(random.uniform(0.85, 1.0), 3)   # high movement = fall
    return {
        "patient_id":  patient_id,
        "heart_rate":  hr,
        "spo2":        round(random.uniform(80, 88), 1),
        "temperature": temp,
        "movement":    mov,
    }


# ── Patient scenario definitions ───────────────────────────────────────────────

class DemoPatient:
    def __init__(self, pid, mode):
        self.pid   = pid
        self.mode  = mode          # "normal" | "warning" | "emergency" | "cycle"
        self._t    = time.time()
        self._phase = 0
        self._phase_names = ["normal", "warning", "emergency_hr",
                             "emergency_temp", "emergency_fall"]
        self._phase_dur   = 15     # seconds per phase in cycle mode

    def next_payload(self):
        if self.mode == "normal":
            return _normal_vitals(self.pid)
        elif self.mode == "warning":
            return _warning_vitals(self.pid)
        elif self.mode == "emergency":
            trigger = random.choice(["hr", "temp", "fall"])
            return _emergency_vitals(self.pid, trigger)
        else:   # cycle
            elapsed = time.time() - self._t
            self._phase = int(elapsed / self._phase_dur) % len(self._phase_names)
            ph = self._phase_names[self._phase]
            remaining = self._phase_dur - (elapsed % self._phase_dur)
            if ph == "normal":
                p = _normal_vitals(self.pid)
            elif ph == "warning":
                p = _warning_vitals(self.pid)
            elif ph == "emergency_hr":
                p = _emergency_vitals(self.pid, "hr")
            elif ph == "emergency_temp":
                p = _emergency_vitals(self.pid, "temp")
            else:
                p = _emergency_vitals(self.pid, "fall")
            p["_demo_phase"]     = ph
            p["_phase_remaining"] = round(remaining, 1)
            return p


# ── Main ───────────────────────────────────────────────────────────────────────

PATIENTS = [
    DemoPatient("DEMO-1", "normal"),
    DemoPatient("DEMO-2", "warning"),
    DemoPatient("DEMO-3", "emergency"),
    DemoPatient("DEMO-4", "cycle"),
]

CASE_LABELS = {
    "normal":         "NORMAL    (GREEN)   — HR ≤ 120, temp ≤ 38, no fall",
    "warning":        "WARNING   (YELLOW)  — HR 121-149 OR temp 38-40",
    "emergency_hr":   "EMERGENCY (RED)     — HR > 150",
    "emergency_temp": "EMERGENCY (RED)     — temp > 40",
    "emergency_fall": "EMERGENCY (RED)     — fall detected (high movement)",
}


def main():
    parser = argparse.ArgumentParser(description="VitalSense ESP32 demo simulator")
    parser.add_argument("--interval", type=float, default=0.5,
                        help="Publish interval in seconds (default: 0.5)")
    args = parser.parse_args()

    client = mqtt.Client()
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
    except Exception as e:
        print(f"[demo] Could not connect to {config.MQTT_BROKER}:{config.MQTT_PORT} — {e}")
        return

    client.loop_start()

    print("=" * 62)
    print("  VitalSense Demo Simulator  (ESP32 threshold logic)")
    print("=" * 62)
    print(f"  Broker  : {config.MQTT_BROKER}:{config.MQTT_PORT}")
    print(f"  Topic   : {config.MQTT_TOPIC}")
    print(f"  Interval: {args.interval}s")
    print()
    print("  DEMO-1 → always NORMAL    (GREEN)")
    print("  DEMO-2 → always WARNING   (YELLOW)")
    print("  DEMO-3 → always EMERGENCY (RED)")
    print("  DEMO-4 → cycles through all cases every 15 s")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 62)

    try:
        while True:
            for p in PATIENTS:
                payload = p.next_payload()

                # Strip demo-only meta keys before publishing
                phase = payload.pop("_demo_phase", None)
                remaining = payload.pop("_phase_remaining", None)

                client.publish(config.MQTT_TOPIC, json.dumps(payload))

                hr   = payload["heart_rate"]
                spo2 = payload["spo2"]
                temp = payload["temperature"]
                mov  = payload["movement"]

                if phase:
                    label = CASE_LABELS.get(phase, phase)
                    print(f"  [{p.pid}] {label}")
                    print(f"         HR={hr}  SpO2={spo2}  Temp={temp}  Mov={mov}  (next in {remaining}s)")
                else:
                    mode_label = CASE_LABELS.get(p.mode,
                                 CASE_LABELS.get(f"emergency_hr") if p.mode == "emergency" else p.mode)
                    print(f"  [{p.pid}] {mode_label}")
                    print(f"         HR={hr}  SpO2={spo2}  Temp={temp}  Mov={mov}")

            print()
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[demo] Stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
