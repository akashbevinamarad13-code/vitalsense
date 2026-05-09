import argparse
import json
import math
import random
import time
import paho.mqtt.client as mqtt
import config

PROFILES = {
    "P001": "healthy",
    "P002": "deteriorating",
    "P003": "unstable",
    "P004": "recovering",
    "P005": "random",
}

_start = time.time()

def _generate(patient_id, profile):
    t = time.time() - _start
    if profile == "healthy":
        hr = 72 + random.gauss(0, 2)
        spo2 = 98 + random.gauss(0, 0.5)
        temp = 36.8 + random.gauss(0, 0.1)
        mov = abs(random.gauss(0, 0.05))
    elif profile == "deteriorating":
        pct = min(t / 60.0, 1.0)
        hr = 72 + pct * 70 + random.gauss(0, 3)
        spo2 = 98 - pct * 15 + random.gauss(0, 1)
        temp = 36.8 + pct * 2.5 + random.gauss(0, 0.1)
        mov = 0.1 + pct * 0.5 + abs(random.gauss(0, 0.05))
    elif profile == "unstable":
        wave = math.sin(t / 10.0)
        hr = 100 + wave * 30 + random.gauss(0, 5)
        spo2 = 92 + wave * 6 + random.gauss(0, 1)
        temp = 38.0 + wave * 0.8 + random.gauss(0, 0.1)
        mov = abs(0.3 + wave * 0.2 + random.gauss(0, 0.05))
    elif profile == "recovering":
        pct = min(t / 75.0, 1.0)
        hr = 140 - pct * 68 + random.gauss(0, 3)
        spo2 = 85 + pct * 13 + random.gauss(0, 1)
        temp = 39.5 - pct * 2.5 + random.gauss(0, 0.1)
        mov = 0.6 - pct * 0.5 + abs(random.gauss(0, 0.05))
    else:
        hr = random.uniform(55, 145)
        spo2 = random.uniform(82, 100)
        temp = random.uniform(36.0, 40.0)
        mov = random.uniform(0.0, 1.0)

    return {
        "patient_id": patient_id,
        "heart_rate": round(max(40.0, min(200.0, hr)), 1),
        "spo2": round(max(70.0, min(100.0, spo2)), 1),
        "temperature": round(max(34.0, min(42.0, temp)), 2),
        "movement": round(max(0.0, mov), 3),
    }


def main():
    parser = argparse.ArgumentParser(description="VitalSense ESP32 simulator")
    parser.add_argument("--patients", nargs="+", default=list(PROFILES.keys()),
                        help="Patient IDs to simulate (default: all 5)")
    parser.add_argument("--interval", type=float, default=0.5,
                        help="Publish interval in seconds (default: 0.5)")
    args = parser.parse_args()

    client = mqtt.Client()
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
    except Exception as e:
        print(f"[simulator] Could not connect to {config.MQTT_BROKER}:{config.MQTT_PORT} — {e}")
        return

    client.loop_start()
    print(f"[simulator] Publishing {len(args.patients)} patient(s) every {args.interval}s to {config.MQTT_TOPIC}")
    print(f"[simulator] Patients: {', '.join(args.patients)}")
    print("[simulator] Press Ctrl+C to stop\n")

    try:
        while True:
            for pid in args.patients:
                profile = PROFILES.get(pid, "random")
                payload = _generate(pid, profile)
                client.publish(config.MQTT_TOPIC, json.dumps(payload))
                print(f"  → {pid} ({profile}): HR={payload['heart_rate']}  SpO2={payload['spo2']}  Temp={payload['temperature']}  Mov={payload['movement']}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[simulator] Stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
