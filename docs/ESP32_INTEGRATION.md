# Connecting a real ESP32 (hardware integration guide)

Status: **the backend side is implemented; the ESP32 firmware below is an untested example** – adapt it to the sensors you buy.

## 1. Decide what the sensor can measure
| Sensor | Measures | Backend `sensor_type` | Notes |
|---|---|---|---|
| DHT22 / BME280 | temperature, humidity | `temperature`, `humidity` | |
| PIR | **presence only** | `occupancy` with `sensing_mode = presence` | value 0/1. **Not a head count.** The over-capacity rule ignores presence sensors. |
| CO₂ / air-quality sensor | CO₂-eq. ppm | `air_quality` | choose thresholds from the sensor datasheet |

## 2. Register the device (administrator)
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@asiet.demo","password":"Admin@123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8000/api/devices -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{
  "device_uid": "ESP32-A1B2C3",
  "name": "IoT Lab node",
  "room_id": 15,
  "sensors": [
    {"type": "temperature", "unit": "°C"},
    {"type": "humidity", "unit": "%"},
    {"type": "occupancy", "unit": "presence", "sensing_mode": "presence"}
  ]
}'
```
`room_id` comes from `GET /api/rooms`. The device-to-location mapping is stored in the database.

## 3. Send readings
```bash
curl -X POST http://localhost:8000/api/ingest -H "X-Device-Key: esp32-dev-key" -H "Content-Type: application/json" \
  -d '{"device_uid":"ESP32-A1B2C3","readings":[{"sensor_type":"temperature","value":28.4},{"sensor_type":"humidity","value":64},{"sensor_type":"occupancy","value":1}]}'
```
* Values are range-checked (e.g. temperature −40…85 °C); invalid values are rejected and reported in the response.
* The server's receive time is used as the timestamp.
* Readings are stored with `is_simulated = 0` and shown as HARDWARE in the UI.
* A device is "offline" when it has sent nothing for the configured time (rule *Device offline*, default 60 s).
* Set `SIMULATOR_ENABLED=0` to stop the simulator when only real devices should appear.

## 4. Example Arduino sketch (UNTESTED – adjust pins, libraries and sensor code)
```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASS = "YOUR_PASSWORD";
const char* SERVER_URL = "http://192.168.1.20:8000/api/ingest";   // PC running the backend
const char* DEVICE_KEY = "esp32-dev-key";
const char* DEVICE_UID = "ESP32-A1B2C3";                          // must match the registered device

float readTemperature() { return 28.4; }  // TODO: replace with your sensor library call
float readHumidity()    { return 64.0; }  // TODO
int   readPresence()    { return 1; }     // TODO: PIR pin -> 0/1

void setup() {
  Serial.begin(115200);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    String body = String("{\"device_uid\":\"") + DEVICE_UID + "\",\"readings\":[" +
      "{\"sensor_type\":\"temperature\",\"value\":" + String(readTemperature(), 1) + "}," +
      "{\"sensor_type\":\"humidity\",\"value\":" + String(readHumidity(), 1) + "}," +
      "{\"sensor_type\":\"occupancy\",\"value\":" + String(readPresence()) + "}]}";
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Key", DEVICE_KEY);
    int code = http.POST(body);
    Serial.println(code);
    http.end();
  }
  delay(10000);  // one message every 10 s
}
```
The backend must be started with `--host 0.0.0.0` so that the ESP32 can reach it: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

## 5. Hardware test checklist (record real results in the report)
- [ ] ESP32 connects to Wi-Fi and reaches `/api/health`
- [ ] Reading appears in Live Monitoring with tag HARDWARE
- [ ] Unplug the ESP32 → device becomes offline and an alert is generated
- [ ] Measure end-to-end latency (sensor → dashboard) before claiming "real-time"
