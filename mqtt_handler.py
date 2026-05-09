import json
import time
import eventlet
import paho.mqtt.client as mqtt
import config
import patient_store
import alert as alert_handler

_client = None
_socketio = None
_model = None
_features = None
_connected = False
_reconnect_attempts = 0
_connected_since = None

def patient_room(patient_id):
    return f"patient_{patient_id}"

def on_connect(client, userdata, flags, rc):
    global _connected, _reconnect_attempts, _connected_since
    if rc == 0:
        _connected = True
        _reconnect_attempts = 0
        _connected_since = time.time()
        client.subscribe(config.MQTT_TOPIC)
        print(f"[mqtt_handler] Connected to broker {config.MQTT_BROKER}:{config.MQTT_PORT}")
        print(f"[mqtt_handler] Subscribed to topic: {config.MQTT_TOPIC}")
    else:
        print(f"[mqtt_handler] Connection failed with code {rc}")

def on_disconnect(client, userdata, rc):
    global _connected
    _connected = False
    print(f"[mqtt_handler] Disconnected from broker (rc={rc})")

def on_message(client, userdata, msg):
    global _socketio, _model, _features
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        patient_id = payload["patient_id"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[mqtt_handler] Payload parse error: {e}")
        return
    except Exception as e:
        print(f"[mqtt_handler] Unexpected error parsing message: {e}")
        return

    try:
        from classifier import classify
        severity_int, severity, color, confidence = classify(_model, _features, payload)
    except Exception as e:
        print(f"[mqtt_handler] Classification error for {patient_id}: {e}")
        return

    def _get(d, *keys, default=None):
        for k in keys:
            if k in d:
                return d[k]
        return default

    emit_payload = {
        "patient_id":  patient_id,
        "heart_rate":  _get(payload, "heart_rate", "hr", "heartRate", "heart_rate_bpm"),
        "spo2":        _get(payload, "spo2", "SpO2", "spO2", "oxygen_saturation"),
        "temperature": _get(payload, "temperature", "body_temp", "temp"),
        "movement":    _get(payload, "movement", "accel", "activity", default=0.0),
        "severity_int": severity_int,
        "severity":    severity,
        "color":       color,
        "confidence":  confidence,
    }

    patient_store.update(patient_id, emit_payload)

    alert_status = alert_handler.handle_alert(patient_id, severity_int)

    hr = emit_payload.get("heart_rate", 0)
    sp = emit_payload.get("spo2", 0)
    tm = emit_payload.get("temperature", 0)
    print(f"[mqtt_handler] [{patient_id}] {severity}  HR={hr}  SpO2={sp}  Temp={tm}  Conf={confidence}%")

    if _socketio:
        _socketio.emit("patient_update", emit_payload)
        _socketio.emit("patient_update", emit_payload, room=patient_room(patient_id))
        _socketio.emit("summary_update", patient_store.build_summary())
        _socketio.emit("alert_update", alert_status)
        _socketio.emit("alert_update", alert_status, room=patient_room(patient_id))

def _mqtt_loop():
    global _client, _connected, _reconnect_attempts
    _last_reconnect = 0
    while True:
        try:
            _client.loop(timeout=0.05)
        except Exception:
            pass
        eventlet.sleep(0)

        if not _connected:
            now = time.time()
            if now - _last_reconnect > 5:
                _last_reconnect = now
                try:
                    _reconnect_attempts += 1
                    print(f"[mqtt_handler] Reconnection attempt #{_reconnect_attempts} → {config.MQTT_BROKER}:{config.MQTT_PORT}")
                    _client.reconnect()
                except Exception as e:
                    print(f"[mqtt_handler] Reconnect failed: {e}")

def init(socketio, model, features):
    global _client, _socketio, _model, _features
    _socketio = socketio
    _model = model
    _features = features

    _client = mqtt.Client()
    _client.on_connect = on_connect
    _client.on_disconnect = on_disconnect
    _client.on_message = on_message

    try:
        _client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
        print(f"[mqtt_handler] Connecting to {config.MQTT_BROKER}:{config.MQTT_PORT} ...")
    except Exception as e:
        print(f"[mqtt_handler] Initial connect failed: {e} — will retry in background")

    eventlet.spawn(_mqtt_loop)

def get_status():
    return {
        "mqtt_connected": _connected,
        "broker": config.MQTT_BROKER,
        "port": config.MQTT_PORT,
        "topic": config.MQTT_TOPIC,
        "reconnect_attempts": _reconnect_attempts,
        "reconnect_interval_s": 5,
        "connected_since": _connected_since,
    }
