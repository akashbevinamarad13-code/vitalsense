import config

_consecutive_red = {}
_alerted = set()

try:
    from twilio.rest import Client as TwilioClient
    _twilio_available = True
except ImportError:
    _twilio_available = False

def _send_sms(patient_id):
    if not _twilio_available:
        print(f"[alert] Twilio not installed — skipping SMS for {patient_id}")
        return
    if not all([config.TWILIO_SID, config.TWILIO_TOKEN, config.TWILIO_FROM, config.NURSE_NUMBER]):
        print(f"[alert] Twilio credentials not configured — skipping SMS for {patient_id}")
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
