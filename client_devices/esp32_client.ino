/*
 * For ESP32 client device.
 * Receive a control command from the server via WiFi.
 */

#include <WiFi.h>

const int RELAY_PIN = 2;
const char* wifiSsid = "YourWiFi-SSID";
const char* wifiPassword = "YourWiFiPassword";

// TCP server
IPAddress raspberryPiIp(192, 168, 2, 106); // static IP
const uint16_t raspberryPiPort = 8080;
const size_t receiveBufferSize = 128;

WiFiClient raspberryPiClient;
String receiveBuffer;


void connectToWiFi();
void connectToRaspberryPi();
void receiveData();
void handleMessage(const String& message);
void actionCommand(const String& command);

void setup() {
	Serial.begin(115200);
	pinMode(RELAY_PIN, OUTPUT);
	
	connectToWiFi();
	connectToRaspberryPi();
}

void loop() {
	if (WiFi.status() != WL_CONNECTED) {
		connectToWiFi();
	}

	if (!raspberryPiClient.connected()) {
		connectToRaspberryPi();
	}

	receiveData();
}

void connectToWiFi() {
	Serial.print("Connecting to WiFi");
	WiFi.begin(wifiSsid, wifiPassword);

	while (WiFi.status() != WL_CONNECTED) {
		delay(500);
		Serial.print(".");
	}

	Serial.println();
	Serial.println("WiFi connected");
	Serial.print("ESP32 IP: ");
	Serial.println(WiFi.localIP());
}

void connectToRaspberryPi() {
	while (!raspberryPiClient.connected()) {
		Serial.print("Connecting to Raspberry Pi TCP server...");

		if (raspberryPiClient.connect(raspberryPiIp, raspberryPiPort)) {
			Serial.println("connected");
		} else {
			Serial.println("failed; retrying in 5 seconds");
			delay(5000);
		}
	}
}
	
void receiveData() {
	while (raspberryPiClient.available()) {
		char receivedCharacter = static_cast<char>(raspberryPiClient.read());

		if (receivedCharacter == '\n') {
			receiveBuffer.trim();

			if (receiveBuffer.length() > 0) {
				handleMessage(receiveBuffer);
			}
			receiveBuffer = "";
		}

		else if (receivedCharacter != '\r') {
			if (receiveBuffer.length() < receiveBufferSize - 1) {
				receiveBuffer += receivedCharacter;
			}
		}
	}
}

void handleMessage(const String& message) {
	Serial.print("Received: ");
	Serial.println(message);

	if (message.startsWith("TIMESTAMP:")) {
		Serial.print("Timestamp received: ");
		Serial.println(message.substring(10));
	}

	else if (message.startsWith("CONTROL:")) {
		String command = message.substring(8);
		actionCommand(command);
	}
	
	else {
		Serial.println("Unknown message format");
	}
}


void actionCommand(const String& command) {
	if (command.length() == 0) {
		return;
	}

	if (command == "LightON") {
		Serial.println("Control command: LightON");
		digitalWrite(RELAY_PIN, HIGH);
	} else if (command == "LightOFF") {
		Serial.println("Control command: LightOFF");
		digitalWrite(RELAY_PIN, LOW);
	} else {
		Serial.println("Unknown control command");
	}
}
