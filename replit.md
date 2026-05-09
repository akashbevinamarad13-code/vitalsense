# VitalSense Backend

Real-time patient vitals monitoring backend. Receives sensor data from ESP32 devices (or the simulator) over MQTT, classifies each reading as Green / Yellow / Red using a trained Random Forest model, emits live WebSocket events to the dashboard, and triggers Twilio SMS alerts for critical patients.

## Project structure

```
app.py              Flask + SocketIO entry point
config.py           All settings (reads from env vars)
model_loader.py     Loads model.pkl (dict format: {model, features})
classifier.py       14-feature classification + engineered features
alert.py            Consecutive-RED tracking + Twilio SMS
mqtt_handler.py     MQTT connection (eventlet greenlet), message routing
patient_store.py    Thread-safe in-memory snapshots + rolling history
simulator.py        Multi-patient data simulator (no hardware needed)
create_dummy_model.py  One-time script to generate a placeholder model.pkl
requirements.txt    Python dependencies
templates/
  dashboard.html    Live patient monitoring dashboard
esp32/
  sketch.ino        ESP32 firmware (WiFi + MQTT publishing)
  diagram.json      Wokwi circuit diagram
  libraries.txt     Required Arduino libraries
  wokwi-project.txt Wokwi setup instructions
```

## Environment variables

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

## REST API

| Endpoint | Purpose |
|---|---|
| `GET /` | Live dashboard |
| `GET /health` | Server + model status |
| `GET /api/status` | MQTT connection + active patients |
| `GET /api/summary` | Triage overview (counts + RED list) |
| `GET /api/patients` | All patient snapshots |
| `GET /api/patients/<id>` | One patient snapshot |
| `GET /api/patients/<id>/history` | Rolling 200-reading buffer |
| `GET /api/patients/<id>/history/export` | CSV download |
| `GET /api/patients/<id>/alerts` | Alert counter + SMS status |
| `GET /api/alerts` | All RED-tracked patients |

## WebSocket events (server → client)

| Event | Payload | When |
|---|---|---|
| `patient_update` | Full vitals + severity | Every MQTT message |
| `summary_update` | Triage counts + RED list | Every MQTT message |
| `alert_update` | Consecutive RED count + SMS status | Every MQTT message |

## Running without hardware

```bash
python simulator.py                        # all 5 patients at 500 ms
python simulator.py --patients P002 P003   # specific patients
python simulator.py --interval 1.0         # slower rate
```

## Replacing the model

1. Train a RandomForestClassifier on your dataset with these 14 features (in order):
   `heart_rate, spo2, body_temp, movement, low_spo2, high_hr, high_temp, spo2_hr_risk, temp_hr_risk, spo2_temp_risk, critical_combo, fever_tachycardia, hr_variability, spo2_drop`
2. Save: `joblib.dump({"model": clf, "features": feature_list}, "model.pkl")`
3. Restart the server.

## User preferences

- MQTT broker: broker.hivemq.com (public HiveMQ, no credentials needed)
- MQTT topic: vitalsense/abhishek/patients
- Alert threshold: 3 consecutive RED readings before SMS fires
- Nurse SMS number: +918123528157
