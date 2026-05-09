import joblib
import os

_model = None
_features = None

def load_model(path="model.pkl"):
    global _model, _features
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"model.pkl not found at '{path}'. "
            "Place your trained model file in the project root."
        )
    raw = joblib.load(path)
    if isinstance(raw, dict) and "model" in raw:
        _model = raw["model"]
        _features = raw.get("features", [])
        print(f"[model_loader] Loaded dict-wrapped model: {type(_model).__name__}")
        print(f"[model_loader] Features ({len(_features)}): {_features}")
    else:
        _model = raw
        _features = []
        print(f"[model_loader] Loaded plain model: {type(_model).__name__}")
    return _model, _features

def get_model():
    return _model

def get_features():
    return _features
