import numpy as np
import pandas as pd

SEVERITY_MAP = {
    0: ("Green", "#22c55e"),
    1: ("Yellow", "#f59e0b"),
    2: ("Red", "#ef4444"),
}

def _engineer_features(heart_rate, spo2, body_temp, movement):
    low_spo2 = 1 if spo2 < 95 else 0
    high_hr = 1 if heart_rate > 100 else 0
    high_temp = 1 if body_temp > 38.0 else 0
    spo2_hr_risk = (100 - spo2) * heart_rate / 100
    temp_hr_risk = body_temp * heart_rate / 100
    spo2_temp_risk = (100 - spo2) * body_temp / 100
    critical_combo = 1 if (spo2 < 90 and heart_rate > 110) else 0
    fever_tachycardia = 1 if (body_temp > 38.5 and heart_rate > 100) else 0
    hr_variability = heart_rate * movement
    spo2_drop = max(0.0, 98.0 - spo2)
    return {
        "heart_rate": heart_rate,
        "spo2": spo2,
        "body_temp": body_temp,
        "movement": movement,
        "low_spo2": low_spo2,
        "high_hr": high_hr,
        "high_temp": high_temp,
        "spo2_hr_risk": spo2_hr_risk,
        "temp_hr_risk": temp_hr_risk,
        "spo2_temp_risk": spo2_temp_risk,
        "critical_combo": critical_combo,
        "fever_tachycardia": fever_tachycardia,
        "hr_variability": hr_variability,
        "spo2_drop": spo2_drop,
    }

def classify(model, features_order, vitals: dict):
    heart_rate = float(vitals["heart_rate"])
    spo2 = float(vitals["spo2"])
    body_temp = float(vitals.get("temperature", vitals.get("body_temp", 37.0)))
    movement = float(vitals.get("movement", 0.0))

    feature_dict = _engineer_features(heart_rate, spo2, body_temp, movement)

    if features_order:
        col_order = features_order
    else:
        col_order = list(feature_dict.keys())

    df = pd.DataFrame([feature_dict], columns=col_order)

    raw_pred = model.predict(df)[0]
    severity_int = int(np.clip(int(raw_pred), 0, 2))

    try:
        proba = model.predict_proba(df)[0]
        confidence = round(float(proba[severity_int]) * 100, 1)
    except Exception:
        confidence = 100.0

    label, color = SEVERITY_MAP[severity_int]
    return severity_int, label, color, confidence
