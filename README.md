# VitalSense — Real-Time Patient Vitals Monitoring System

AI-powered emergency triage dashboard that receives live sensor data from ESP32 devices over MQTT, classifies each reading using a trained Random Forest model, and displays results on a React dashboard with Twilio SMS alerts for critical patients.

---

## Features

- Live vitals monitoring (Heart Rate, SpO2, Body Temperature, Movement)
- AI triage classification — GREEN / YELLOW / RED severity
- Real-time React dashboard via WebSocket
- Twilio SMS alerts after 3 consecutive RED readings
- SMS enable/disable toggle with persistent state
- CSV export of patient history
- Works with real ESP32 hardware or the built-in simulator
- REST API for all patient data

---

## Project Structure

```
VitalSense/
├── app.py                  Flask + SocketIO server (entry point)
├── alert.py                SMS alerts + toggle persistence
├── classifier.py           14-feature ML classification engine
├── config.py               All settings (reads from env vars)
├── model_loader.py         Loads model.pkl
├── mqtt_handler.py         MQTT connection and message routing
├── patient_store.py        Thread-safe in-memory patient store
├── simulator.py            Multi-patient MQTT simulator
├── demo_simulator.py       4-patient demo (GREEN/YELLOW/RED/cycling)
├── create_dummy_model.py   One-time script to generate model.pkl
├── requirements.txt        Python dependencies
├── templates/
│   └── dashboard.html      Live React dashboard
└── esp32/
    ├── sketch.ino          Arduino firmware
    ├── diagram.json        Wokwi circuit diagram
    ├── libraries.txt       Required Arduino libraries
    └── wokwi-project.txt   Wokwi simulator setup guide
```

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/your-username/vitalsense.git
cd vitalsense
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate the placeholder ML model

```bash
python create_dummy_model.py
```

> To use a real trained model, see the **Replacing the Model** section below.

### 4. Set environment variables (optional — needed for SMS)

```bash
export TWILIO_SID=your_account_sid
export TWILIO_TOKEN=your_auth_token
export TWILIO_FROM=+1xxxxxxxxxx
export NURSE_NUMBER=+91xxxxxxxxxx
```

### 5. Start the server

```bash
python app.py
```

Open your browser at `http://localhost:5000`

---

## Running Without Hardware

Use the demo simulator — no ESP32 needed:

```bash
# All 4 demo patients (GREEN / YELLOW / RED / cycling)
python demo_simulator.py

# All 5 patients from the full simulator
python simulator.py

# Specific patients only
python simulator.py --patients P002 P003

# Slower data rate
python simulator.py --interval 1.0
```

Demo patients:
| Patient | Behaviour |
|---|---|
| DEMO-1 | Always GREEN (normal vitals) |
| DEMO-2 | Always YELLOW (elevated HR or temp) |
| DEMO-3 | Always RED (critical — HR > 150 or SpO2 < 88) |
| DEMO-4 | Cycles through all states every 15 seconds |

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `MQTT_BROKER` | MQTT broker hostname | `broker.hivemq.com` |
| `MQTT_PORT` | MQTT broker port | `1883` |
| `MQTT_TOPIC` | Topic to subscribe | `vitalsense/abhishek/patients` |
| `TWILIO_SID` | Twilio account SID | — |
| `TWILIO_TOKEN` | Twilio auth token | — |
| `TWILIO_FROM` | Twilio sender number | — |
| `NURSE_NUMBER` | Nurse SMS recipient | — |
| `PORT` | Flask server port | `5000` |

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Live dashboard |
| GET | `/health` | Server + model status |
| GET | `/api/status` | MQTT connection + active patients |
| GET | `/api/summary` | Triage counts + RED list |
| GET | `/api/patients` | All patient snapshots |
| GET | `/api/patients/<id>` | Single patient snapshot |
| GET | `/api/patients/<id>/history` | Rolling 200-reading buffer |
| GET | `/api/patients/<id>/history/export` | CSV download |
| GET | `/api/patients/<id>/alerts` | Alert counter + SMS status |
| GET | `/api/alerts` | All RED-tracked patients |
| POST | `/api/sms/enable` | Enable SMS alerts |
| POST | `/api/sms/disable` | Disable SMS alerts |
| POST | `/api/alerts/reset` | Reset all consecutive RED counters |

---

## WebSocket Events (Server → Client)

| Event | Payload | Fired when |
|---|---|---|
| `patient_update` | Full vitals + severity + confidence | Every MQTT message |
| `summary_update` | Triage counts + RED patient list | Every MQTT message |
| `alert_update` | Consecutive RED count + SMS status | Every MQTT message |

---

## MQTT Message Format

Publish JSON to the configured topic. The backend accepts multiple field name aliases for cross-device compatibility.

```json
{
  "patient_id": "P001",
  "heart_rate": 85,
  "spo2": 97,
  "body_temp": 36.8,
  "movement": 0.02
}
```

Accepted field aliases:
- Heart rate: `heart_rate`, `hr`, `heartRate`
- SpO2: `spo2`, `SpO2`, `oxygen`
- Temperature: `body_temp`, `temp`, `temperature`
- Movement: `movement`, `accel`, `activity`

---

## Triage Classification Rules

The Random Forest model uses 14 engineered features. The built-in simulator also applies these ESP32-compatible threshold rules:

| Severity | Condition |
|---|---|
| RED | HR > 150, OR Body Temp > 40°C, OR fall detected (movement spike) |
| YELLOW | HR 121–150, OR Body Temp 38–40°C, OR SpO2 88–94% |
| GREEN | All values within normal range |

---

## ESP32 Hardware Setup

### Components

| Component | Purpose | Pin |
|---|---|---|
| DHT22 sensor | Body temperature | GPIO 4 |
| Potentiometer 1 | Simulates Heart Rate (60–180 bpm) | GPIO 34 (ADC) |
| Potentiometer 2 | Simulates SpO2 (80–100%) | GPIO 35 (ADC) |
| MPU6050 (I2C) | Movement + fall detection | SDA 21 / SCL 22 |
| LED (Green) | GREEN triage indicator | GPIO 19 |
| LED (Yellow) | YELLOW triage indicator | GPIO 5 |
| LED (Red) | RED triage indicator | GPIO 18 |

### Wiring Diagram

```
ESP32
├── GPIO 4   → DHT22 data pin (3.3V + 10kΩ pull-up)
├── GPIO 34  → Potentiometer 1 wiper (ADC — Heart Rate)
├── GPIO 35  → Potentiometer 2 wiper (ADC — SpO2)
├── GPIO 21  → MPU6050 SDA
├── GPIO 22  → MPU6050 SCL
├── GPIO 19  → Green LED (+ 220Ω resistor → GND)
├── GPIO 5   → Yellow LED (+ 220Ω resistor → GND)
└── GPIO 18  → Red LED (+ 220Ω resistor → GND)
```

### Required Arduino Libraries

```
PubSubClient       (MQTT)
DHT sensor library (Adafruit)
Adafruit Unified Sensor
MPU6050 (ElectronicCats or Adafruit)
ArduinoJson
WiFi (built-in ESP32)
```

### Firmware Configuration

Edit the top of `esp32/sketch.ino`:

```cpp
const char* ssid     = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "broker.hivemq.com";
const char* patient_id  = "P001";
```

### Testing with Wokwi (no hardware needed)

See `esp32/wokwi-project.txt` for step-by-step instructions to run the firmware in the Wokwi online simulator with a virtual ESP32 circuit.

---

## Replacing the ML Model

1. Train a `RandomForestClassifier` on your dataset with these 14 features **in this exact order**:

```
heart_rate, spo2, body_temp, movement,
low_spo2, high_hr, high_temp,
spo2_hr_risk, temp_hr_risk, spo2_temp_risk,
critical_combo, fever_tachycardia,
hr_variability, spo2_drop
```

2. Save the model:

```python
import joblib
joblib.dump({"model": clf, "features": feature_list}, "model.pkl")
```

3. Restart the server — it loads `model.pkl` automatically on startup.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask, Flask-SocketIO, eventlet |
| ML | scikit-learn (RandomForestClassifier), joblib, pandas, numpy |
| Messaging | paho-mqtt, Twilio SMS |
| Frontend | React 18, Tailwind CSS, Lucide Icons, Babel (in-browser) |
| Transport | MQTT (HiveMQ public broker), WebSocket (Socket.IO) |
| Hardware | ESP32, DHT22, MPU6050, potentiometers, LEDs |

---

## License

MIT License — free to use, modify, and distribute.
