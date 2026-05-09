import eventlet
eventlet.monkey_patch()

import csv
import io
import time
import os
from flask import Flask, jsonify, request, Response, render_template
from flask_socketio import SocketIO, join_room, leave_room

import config
import patient_store
import alert as alert_handler
import mqtt_handler
from model_loader import load_model, get_model, get_features

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "vitalsense-secret-key")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

_model_path = "model.pkl"
_model_loaded = False
_model_error = None


def _try_load_model():
    global _model_loaded, _model_error
    try:
        load_model(_model_path)
        _model_loaded = True
        print(f"[app] Model loaded successfully")
    except FileNotFoundError as e:
        _model_error = str(e)
        print(f"[app] WARNING: {e}")
        print("[app] Server starting without model — classification will fail until model.pkl is added")


# ---------------------------------------------------------------------------
# SocketIO events
# ---------------------------------------------------------------------------

@socketio.on("connect")
def on_client_connect():
    print(f"[app] Client connected: {request.sid}")

@socketio.on("disconnect")
def on_client_disconnect():
    print(f"[app] Client disconnected: {request.sid}")

@socketio.on("subscribe_patient")
def on_subscribe_patient(data):
    pid = data.get("patient_id")
    if pid:
        join_room(mqtt_handler.patient_room(pid))
        print(f"[app] Client joined room: {mqtt_handler.patient_room(pid)} ✅")

@socketio.on("unsubscribe_patient")
def on_unsubscribe_patient(data):
    pid = data.get("patient_id")
    if pid:
        leave_room(mqtt_handler.patient_room(pid))

@socketio.on("subscribe_patients")
def on_subscribe_patients(data):
    for pid in data.get("patient_ids", []):
        join_room(mqtt_handler.patient_room(pid))
        print(f"[app] Client joined room: {mqtt_handler.patient_room(pid)} ✅")

@socketio.on("unsubscribe_patients")
def on_unsubscribe_patients(data):
    for pid in data.get("patient_ids", []):
        leave_room(mqtt_handler.patient_room(pid))


# ---------------------------------------------------------------------------
# REST routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "model_loaded": _model_loaded,
        "model_error": _model_error,
        "timestamp": time.time(),
    })

@app.route("/api/status")
def api_status():
    all_patients = patient_store.get_all()
    return jsonify({
        "server": "ok",
        "model": _model_path if _model_loaded else None,
        "mqtt": mqtt_handler.get_status(),
        "patients": {
            "active": len(all_patients),
            "ids": sorted(all_patients.keys()),
        },
    })

@app.route("/api/summary")
def api_summary():
    return jsonify(patient_store.build_summary())

@app.route("/api/patients")
def api_patients():
    return jsonify(list(patient_store.get_all().values()))

@app.route("/api/patients/<patient_id>")
def api_patient(patient_id):
    snap = patient_store.get_patient(patient_id)
    if snap is None:
        return jsonify({"error": f"Patient '{patient_id}' not found"}), 404
    return jsonify(snap)

@app.route("/api/patients/<patient_id>/history")
def api_patient_history(patient_id):
    limit_param = request.args.get("limit")
    limit = None
    if limit_param is not None:
        try:
            limit = max(1, min(int(limit_param), config.HISTORY_MAX_SIZE))
        except ValueError:
            return jsonify({"error": "limit must be an integer"}), 400
    readings = patient_store.get_history(patient_id, limit=limit)
    return jsonify({
        "patient_id": patient_id,
        "count": len(readings),
        "readings": readings,
    })

@app.route("/api/patients/<patient_id>/history/export")
def api_patient_history_export(patient_id):
    limit_param = request.args.get("limit")
    limit = None
    if limit_param is not None:
        try:
            limit = max(1, min(int(limit_param), config.HISTORY_MAX_SIZE))
        except ValueError:
            return jsonify({"error": "limit must be an integer"}), 400
    readings = patient_store.get_history(patient_id, limit=limit)

    fieldnames = [
        "patient_id", "heart_rate", "spo2", "temperature", "movement",
        "severity_int", "severity", "color", "confidence", "last_seen",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(readings)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=vitalsense_{patient_id}_history.csv"
        },
    )

@app.route("/api/patients/<patient_id>/alerts")
def api_patient_alerts(patient_id):
    return jsonify(alert_handler.get_alert_status(patient_id))

@app.route("/api/alerts")
def api_all_alerts():
    return jsonify(alert_handler.get_all_alert_statuses())


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _try_load_model()
    mqtt_handler.init(socketio, get_model(), get_features())
    print(f"[app] Starting VitalSense backend on port {config.FLASK_PORT}")
    socketio.run(app, host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)
