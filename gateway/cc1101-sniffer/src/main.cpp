#include <Arduino.h>
#include "cc1101.h"

// Define Pins
#define SCK  18
#define MISO 19
#define MOSI 23
#define SS   5
#define GDO0 22
#define GDO2 21

CC1101 radio(SS, GDO0, GDO2);

// Configurations to scan
float frequencies[] = {907.83, 907.47, 924.08, 909.56, 911.59, 904.78, 906.40};
float rates[] = {2.4, 10, 38.4, 50, 100, 250};
uint16_t sync_words[] = {0xD391, 0x7A0E, 0x930B, 0x0000, 0x5555, 0xAAAA};
Modulation modulations[] = {MOD_2FSK, MOD_GFSK};
float deviations[] = {25.4, 47.6, 95.2, 126.9, 190.4};
bool manchester[] = {true, false};

// Modes
enum Mode {
    MODE_SCAN,
    MODE_SNIFF
};

Mode currentMode = MODE_SCAN;

// Scan state
int freq_idx = 0;
int rate_idx = 0;
int sync_idx = 0;
int mod_idx = 0;
int dev_idx = 0;
int manch_idx = 0;

unsigned long lastConfigTime = 0;
const unsigned long SCAN_INTERVAL = 2000; // 2 seconds per config

void setupConfig() {
    radio.setFrequency(frequencies[freq_idx]);
    radio.setDataRate(rates[rate_idx]);
    radio.setModulation(modulations[mod_idx]);
    radio.setDeviation(deviations[dev_idx]);
    radio.setSyncWord(sync_words[sync_idx]);
    radio.setManchester(manchester[manch_idx]);
    radio.setRxBandwidth(500.0); // wide bandwidth for sniffing
    radio.startRx();
}

void printConfig(bool match) {
    if (match) {
        Serial.println("\n*** MATCH FOUND ***");
    } else {
        Serial.println("\n--- Scanning Config ---");
    }
    Serial.printf("Freq: %.3f MHz\n", frequencies[freq_idx]);
    Serial.printf("Rate: %.1f kbps\n", rates[rate_idx]);
    Serial.printf("Mod: %s\n", modulations[mod_idx] == MOD_2FSK ? "2-FSK" : "GFSK");
    Serial.printf("Dev: %.1f kHz\n", deviations[dev_idx]);
    Serial.printf("Sync: 0x%04X\n", sync_words[sync_idx]);
    Serial.printf("Manchester: %s\n", manchester[manch_idx] ? "ON" : "OFF");
}

void nextConfig() {
    manch_idx++;
    if (manch_idx >= sizeof(manchester)/sizeof(manchester[0])) { manch_idx = 0; dev_idx++; }
    if (dev_idx >= sizeof(deviations)/sizeof(deviations[0])) { dev_idx = 0; mod_idx++; }
    if (mod_idx >= sizeof(modulations)/sizeof(modulations[0])) { mod_idx = 0; sync_idx++; }
    if (sync_idx >= sizeof(sync_words)/sizeof(sync_words[0])) { sync_idx = 0; rate_idx++; }
    if (rate_idx >= sizeof(rates)/sizeof(rates[0])) { rate_idx = 0; freq_idx++; }
    if (freq_idx >= sizeof(frequencies)/sizeof(frequencies[0])) { freq_idx = 0; }
    
    setupConfig();
    printConfig(false);
}

void setup() {
    Serial.begin(115200);
    while (!Serial);

    Serial.println("Starting CC1101 Sniffer...");

    if (!radio.init()) {
        Serial.println("CC1101 Initialization failed!");
        while (1) delay(100);
    }
    
    Serial.println("CC1101 Initialized.");
    setupConfig();
    printConfig(false);
    lastConfigTime = millis();
}

void loop() {
    uint8_t buffer[64];
    uint8_t len = sizeof(buffer);
    
    if (radio.receivePacket(buffer, &len)) {
        if (currentMode == MODE_SCAN) {
            printConfig(true);
            currentMode = MODE_SNIFF; // Lock onto this config
            Serial.println("Switching to SNIFF mode...");
        }
        
        Serial.printf("RSSI: %d dBm\n", radio.getRSSI());
        Serial.printf("LQI: %d\n", radio.getLQI());
        Serial.printf("Packet (%d bytes): ", len);
        for (int i = 0; i < len; i++) {
            Serial.printf("%02X ", buffer[i]);
        }
        Serial.println();
    }
    
    if (currentMode == MODE_SCAN) {
        if (millis() - lastConfigTime >= SCAN_INTERVAL) {
            nextConfig();
            lastConfigTime = millis();
        }
    }
}
