#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <MPU6050.h>
#include "DHT.h"

// ── WiFi / MQTT config ────────────────────────────────────────────────────────
const char* SSID        = "Wokwi-GUEST";
const char* WIFI_PASS   = "";
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;
const char* MQTT_TOPIC  = "vitalsense/abhishek/patients";
const char* PATIENT_ID  = "P001";   // Change per device before flashing

// ── Pin mapping ───────────────────────────────────────────────────────────────
#define DHTPIN       4     // DHT22 data  (matches your wiring)
#define DHTTYPE      DHT22

#define POT_PIN      34    // Potentiometer → heart rate (0-4095 → 60-180 bpm)
#define SPO2_POT_PIN 35    // Potentiometer → SpO2       (0-4095 → 80-100 %)

#define GREEN_LED    19
#define YELLOW_LED   5
#define RED_LED      18

// MPU6050 uses default I2C pins (SDA=21, SCL=22)

// ── Objects ───────────────────────────────────────────────────────────────────
DHT      dht(DHTPIN, DHTTYPE);
MPU6050  mpu;
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);

// ── Helpers ───────────────────────────────────────────────────────────────────
float mapFloat(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) / (in_max - in_min) * (out_max - out_min) + out_min;
}

void ledsOff() {
  digitalWrite(GREEN_LED,  LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(RED_LED,    LOW);
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

  pinMode(GREEN_LED,  OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(RED_LED,    OUTPUT);
  ledsOff();

  dht.begin();

  Wire.begin();
  mpu.initialize();
  if (!mpu.testConnection()) {
    Serial.println("MPU6050 connection failed — using 0 for movement.");
  }

  connectWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);

  Serial.println("VitalSense Started");
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
  if (!mqtt.connected()) connectMQTT();
  mqtt.loop();

  // ── Sensors ────────────────────────────────────────────────────────────────

  // Temperature from DHT22
  float temperature = dht.readTemperature();
  if (isnan(temperature)) temperature = 37.0;

  // Heart rate from potentiometer (0-4095 → 60-180 bpm)
  int   potValue  = analogRead(POT_PIN);
  float heartRate = map(potValue, 0, 4095, 60, 180);

  // SpO2 from second potentiometer (0-4095 → 80-100 %)
  int   spo2Raw = analogRead(SPO2_POT_PIN);
  float spo2    = mapFloat(spo2Raw, 0, 4095, 80.0, 100.0);

  // Movement / fall detection from MPU6050
  int16_t ax, ay, az;
  mpu.getAcceleration(&ax, &ay, &az);
  bool  fallDetected = (abs(ax) > 20000 || abs(ay) > 20000);
  float movement     = constrain(
                         (float)(abs(ax) + abs(ay) + abs(az)) / 98000.0,
                         0.0, 1.0);

  // ── Serial monitor ─────────────────────────────────────────────────────────
  Serial.println("====== VitalSense ======");
  Serial.print("Temperature : "); Serial.println(temperature);
  Serial.print("Heart Rate  : "); Serial.println((int)heartRate);
  Serial.print("SpO2        : "); Serial.println(spo2);
  Serial.print("Movement    : "); Serial.println(movement);
  Serial.print("Fall        : "); Serial.println(fallDetected ? "YES" : "NO");

  // ── Triage decision (mirrors the ML backend thresholds) ───────────────────
  ledsOff();

  String status;
  if (temperature > 40 || heartRate > 150 || fallDetected) {
    digitalWrite(RED_LED, HIGH);
    status = "EMERGENCY (RED)";
  } else if (temperature > 38 || heartRate > 120) {
    digitalWrite(YELLOW_LED, HIGH);
    status = "WARNING (YELLOW)";
  } else {
    digitalWrite(GREEN_LED, HIGH);
    status = "NORMAL (GREEN)";
  }

  Serial.print("STATUS      : "); Serial.println(status);
  Serial.println();

  // ── Publish to MQTT ────────────────────────────────────────────────────────
  StaticJsonDocument<256> doc;
  doc["patient_id"]  = PATIENT_ID;
  doc["heart_rate"]  = (float)((int)(heartRate * 10)) / 10.0;
  doc["spo2"]        = (float)((int)(spo2 * 10)) / 10.0;
  doc["temperature"] = (float)((int)(temperature * 100)) / 100.0;
  doc["movement"]    = (float)((int)(movement * 1000)) / 1000.0;

  char buf[256];
  serializeJson(doc, buf);
  mqtt.publish(MQTT_TOPIC, buf);
  Serial.print("Published   : "); Serial.println(buf);

  delay(500);
}
