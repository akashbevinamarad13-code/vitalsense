"""
Run this once to generate a dummy model.pkl so the server can start.
Replace with your real trained model when ready.
"""
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier

FEATURES = [
    "heart_rate", "spo2", "body_temp", "movement",
    "low_spo2", "high_hr", "high_temp",
    "spo2_hr_risk", "temp_hr_risk", "spo2_temp_risk",
    "critical_combo", "fever_tachycardia",
    "hr_variability", "spo2_drop",
]

def make_row(hr, spo2, temp, mov):
    low_spo2 = 1 if spo2 < 95 else 0
    high_hr = 1 if hr > 100 else 0
    high_temp = 1 if temp > 38.0 else 0
    return [
        hr, spo2, temp, mov,
        low_spo2, high_hr, high_temp,
        (100 - spo2) * hr / 100,
        temp * hr / 100,
        (100 - spo2) * temp / 100,
        1 if (spo2 < 90 and hr > 110) else 0,
        1 if (temp > 38.5 and hr > 100) else 0,
        hr * mov,
        max(0.0, 98.0 - spo2),
    ]

rng = np.random.default_rng(42)

X, y = [], []
for _ in range(400):
    hr = rng.uniform(55, 85); spo2 = rng.uniform(96, 100); temp = rng.uniform(36.5, 37.5); mov = rng.uniform(0, 0.2)
    X.append(make_row(hr, spo2, temp, mov)); y.append(0)
for _ in range(300):
    hr = rng.uniform(90, 115); spo2 = rng.uniform(90, 96); temp = rng.uniform(37.8, 39.0); mov = rng.uniform(0.2, 0.5)
    X.append(make_row(hr, spo2, temp, mov)); y.append(1)
for _ in range(300):
    hr = rng.uniform(115, 160); spo2 = rng.uniform(80, 90); temp = rng.uniform(38.8, 41.0); mov = rng.uniform(0.4, 1.0)
    X.append(make_row(hr, spo2, temp, mov)); y.append(2)

import pandas as pd
X = pd.DataFrame(X, columns=FEATURES)
y = np.array(y)
clf = RandomForestClassifier(n_estimators=50, random_state=42)
clf.fit(X, y)

joblib.dump({"model": clf, "features": FEATURES}, "model.pkl")
print("model.pkl created successfully.")
print(f"Test Green: {clf.predict([make_row(72, 98, 37.0, 0.1)])} → {['Green','Yellow','Red'][clf.predict([make_row(72, 98, 37.0, 0.1)])[0]]}")
print(f"Test Red:   {clf.predict([make_row(140, 85, 39.5, 0.8)])} → {['Green','Yellow','Red'][clf.predict([make_row(140, 85, 39.5, 0.8)])[0]]}")
