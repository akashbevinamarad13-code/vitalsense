#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHTesp.h>

// ── Configuration ────────────────────────────────────────────────────────────
const char* SSID        = "Wokwi-GUEST";
const char* WIFI_PASS   = "";
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;
const char* MQTT_TOPIC  = "vitalsense/abhishek/patients";
const char* PATIENT_ID  = "P001";   // Change per device before flashing

// ── Pin mapping ───────────────────────────────────────────────────────────────
#define DHT_PIN       15    // DHT22 data
#define HR_POT_PIN    34    // Potentiometer → heart rate (0-4095 → 40-180 bpm)
#define SPO2_POT_PIN  35    // Potentiometer → SpO2 (0-4095 → 80-100 %)
#define MPU_SDA       21
#define MPU_SCL       22

DHTesp dht;
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);

// ── Helpers ───────────────────────────────────────────────────────────────────
float mapFloat(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) / (in_max - in_min) * (out_max - out_min) + out_min;
}

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println(" connected. IP: " + WiFi.localIP().toString());
}

void connectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("Connecting to MQTT…");
    String cid = "vitalsense_" + String(PATIENT_ID) + "_" + String(random(0xffff), HEX);
    if (mqtt.connect(cid.c_str())) {
      Serial.println(" connected.");
    } else {
      Serial.println(" failed (rc=" + String(mqtt.state()) + "). Retrying in 3s…");
      delay(3000);
    }
  }
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  dht.setup(DHT_PIN, DHTesp::DHT22);
  connectWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
  if (!mqtt.connected()) connectMQTT();
  mqtt.loop();

  // Read sensors
  TempAndHumidity th = dht.getTempAndHumidity();
  float temperature = isnan(th.temperature) ? 37.0 : th.temperature;

  int hrRaw   = analogRead(HR_POT_PIN);
  int spo2Raw = analogRead(SPO2_POT_PIN);
  float heartRate = mapFloat(hrRaw,   0, 4095, 40.0, 180.0);
  float spo2      = mapFloat(spo2Raw, 0, 4095, 80.0, 100.0);
  float movement  = random(0, 100) / 1000.0;   // MPU6050 proxy

  // Build JSON payload
  StaticJsonDocument<200> doc;
  doc["patient_id"]  = PATIENT_ID;
  doc["heart_rate"]  = round(heartRate * 10) / 10.0;
  doc["spo2"]        = round(spo2 * 10) / 10.0;
  doc["temperature"] = round(temperature * 100) / 100.0;
  doc["movement"]    = movement;

  char buf[200];
  serializeJson(doc, buf);
  mqtt.publish(MQTT_TOPIC, buf);

  Serial.print("Published: "); Serial.println(buf);
  delay(500);
}
