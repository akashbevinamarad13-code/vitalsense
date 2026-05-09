import json
import os
import config

_consecutive_red = {}
_alerted = set()

_STATE_FILE = "sms_state.json"

def _load_sms_state():
    if os.path.exists(_STATE_FILE):
        try:
            with open(_STATE_FILE) as f:
                return json.load(f).get("sms_enabled", config.SMS_ALERTS_ENABLED)
        except Exception:
            pass
    return config.SMS_ALERTS_ENABLED

def _save_sms_state(enabled: bool):
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump({"sms_enabled": enabled}, f)
    except Exception as e:
        print(f"[alert] Could not save SMS state: {e}")

_sms_enabled = _load_sms_state()
print(f"[alert] SMS alerts {'enabled' if _sms_enabled else 'disabled'} (loaded from state)")

try:
    from twilio.rest import Client as TwilioClient
    _twilio_available = True
except ImportError:
    _twilio_available = False

def set_sms_enabled(enabled: bool):
    global _sms_enabled
    _sms_enabled = enabled
    _save_sms_state(enabled)
    print(f"[alert] SMS alerts {'enabled' if enabled else 'disabled'}")

def is_sms_enabled():
    return _sms_enabled

def reset_all():
    global _consecutive_red, _alerted
    _consecutive_red.clear()
    _alerted.clear()
    print("[alert] All alert counters reset")

def reset_patient(patient_id):
    _consecutive_red.pop(patient_id, None)
    _alerted.discard(patient_id)
    print(f"[alert] Alert counter reset for {patient_id}")

_daily_limit_hit = False

def _send_sms(patient_id):
    global _daily_limit_hit
    if not _sms_enabled:
        print(f"[alert] SMS disabled — skipping for {patient_id}")
        return
    if not _twilio_available:
        print(f"[alert] Twilio not installed — skipping SMS for {patient_id}")
        return
    if not all([config.TWILIO_SID, config.TWILIO_TOKEN, config.TWILIO_FROM, config.NURSE_NUMBER]):
        print(f"[alert] Twilio credentials not configured — skipping SMS for {patient_id}")
        return
    if _daily_limit_hit:
        print(f"[alert] Twilio daily limit already reached — skipping SMS for {patient_id}")
        return
    try:
        client = TwilioClient(config.TWILIO_SID, config.TWILIO_TOKEN)
        msg = client.messages.create(
            body=f"[VitalSense ALERT] Patient {patient_id} has had {config.ALERT_THRESHOLD} consecutive RED readings. Immediate attention required.",
            from_=config.TWILIO_FROM,
            to=config.NURSE_NUMBER,
        )
        print(f"[alert] SMS sent successfully for patient {patient_id}. SID: {msg.sid}")
    except Exception as e:
        err_str = str(e)
        if "63038" in err_str or "daily messages limit" in err_str.lower():
            _daily_limit_hit = True
            print(f"[alert] Twilio daily 50-message limit reached. SMS silenced until server restart.")
        else:
            print(f"[alert] SMS failed for patient {patient_id}: {e}")

def handle_alert(patient_id, severity_int):
    if severity_int == 2:
        _consecutive_red[patient_id] = _consecutive_red.get(patient_id, 0) + 1
        if _consecutive_red[patient_id] >= config.ALERT_THRESHOLD and patient_id not in _alerted:
            _alerted.add(patient_id)
            _send_sms(patient_id)
    else:
        _consecutive_red[patient_id] = 0
        _alerted.discard(patient_id)
    return get_alert_status(patient_id)

def get_alert_status(patient_id):
    count = _consecutive_red.get(patient_id, 0)
    sms_sent = patient_id in _alerted
    readings_until = max(0, config.ALERT_THRESHOLD - count)
    return {
        "patient_id": patient_id,
        "consecutive_red_readings": count,
        "alert_threshold": config.ALERT_THRESHOLD,
        "readings_until_alert": readings_until,
        "sms_sent": sms_sent,
    }

def get_all_alert_statuses():
    all_ids = set(_consecutive_red.keys()) | _alerted
    return sorted(
        [get_alert_status(pid) for pid in all_ids],
        key=lambda x: x["patient_id"],
    )
