import os

MQTT_BROKER = os.environ.get("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "vitalsense/abhishek/patients")

TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "")
TWILIO_FROM = os.environ.get("TWILIO_FROM", "")
NURSE_NUMBER = os.environ.get("NURSE_NUMBER", "")

FLASK_HOST = "0.0.0.0"
FLASK_PORT = int(os.environ.get("PORT", 5000))
FLASK_DEBUG = False

ALERT_THRESHOLD = 3
HISTORY_MAX_SIZE = 200
SMS_ALERTS_ENABLED = os.environ.get("SMS_ALERTS_ENABLED", "true").lower() == "true"
