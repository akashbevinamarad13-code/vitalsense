import threading
import time
import collections
import config

_lock = threading.Lock()
_snapshots = {}
_history = {}

def update(patient_id, snapshot):
    snapshot = dict(snapshot)
    snapshot["last_seen"] = time.time()
    with _lock:
        _snapshots[patient_id] = snapshot
        if patient_id not in _history:
            _history[patient_id] = collections.deque(maxlen=config.HISTORY_MAX_SIZE)
        _history[patient_id].append(snapshot)

def get_all():
    with _lock:
        return dict(_snapshots)

def get_patient(patient_id):
    with _lock:
        return _snapshots.get(patient_id)

def get_history(patient_id, limit=None):
    with _lock:
        buf = _history.get(patient_id)
        if buf is None:
            return []
        lst = list(buf)
    if limit is not None:
        lst = lst[-limit:]
    return lst

def build_summary():
    with _lock:
        snapshots = list(_snapshots.values())

    counts = {"Green": 0, "Yellow": 0, "Red": 0}
    red_patients = []

    for s in snapshots:
        sev = s.get("severity", "Green")
        if sev in counts:
            counts[sev] += 1
        if sev == "Red":
            red_patients.append({
                "patient_id": s.get("patient_id"),
                "heart_rate": s.get("heart_rate"),
                "spo2": s.get("spo2"),
                "temperature": s.get("temperature"),
                "confidence": s.get("confidence"),
                "last_seen": s.get("last_seen"),
            })

    red_patients.sort(key=lambda x: x.get("last_seen", 0), reverse=True)

    return {
        "total_active": len(snapshots),
        "severity_counts": counts,
        "red_patients": red_patients,
    }
