#include <Arduino.h>
#include <ELECHOUSE_CC1101_SRC_DRV.h>

// SPI Pins (standard VSPI)
#define CC1101_SCK  18
#define CC1101_MISO 19
#define CC1101_MOSI 23
#define CC1101_CS   5
#define CC1101_GDO0 22   // Current wiring - used for RX data/interrupt

// Known Flair frequencies from SDR analysis
float frequencies[] = {906.40, 907.47, 907.83, 909.56, 904.78, 911.59, 915.00, 924.08};
const int NUM_FREQS = 8;

void setup() {
    Serial.begin(115200);
    while (!Serial);
    
    Serial.println("=== Flair CC1101 Sniffer (ELECHOUSE) ===");
    
    // Initialize CC1101 with explicit SPI pins
    ELECHOUSE_cc1101.setSpiPin(CC1101_SCK, CC1101_MISO, CC1101_MOSI, CC1101_CS);
    ELECHOUSE_cc1101.Init();
    
    if (ELECHOUSE_cc1101.getCC1101()) {
        Serial.println("CC1101 SPI connection OK");
    } else {
        Serial.println("CC1101 not detected!");
        while (true) delay(1000);
    }
    
    // Phase 1: RSSI scan to verify reception at 915 MHz band
    Serial.println("\n--- Phase 1: RSSI Scan ---");
    Serial.println("Scanning Flair frequencies for RF energy...");
    Serial.println("SEND VENT COMMANDS FROM FLAIR APP NOW!\n");
    
    // Quick baseline RSSI scan
    for (int i = 0; i < NUM_FREQS; i++) {
        ELECHOUSE_cc1101.setMHZ(frequencies[i]);
        ELECHOUSE_cc1101.SetRx();
        delay(10);
        
        int8_t maxRssi = -128;
        for (int s = 0; s < 100; s++) {
            int8_t rssi = ELECHOUSE_cc1101.getRssi();
            if (rssi > maxRssi) maxRssi = rssi;
            delayMicroseconds(500);
        }
        Serial.printf("  %.2f MHz: max RSSI = %d dBm\n", frequencies[i], maxRssi);
    }
    
    // Phase 2: Fast RSSI monitoring with spike detection
    Serial.println("\n--- Phase 2: Continuous RSSI Monitor ---");
    Serial.println("Watching for signal spikes...");
    Serial.println("Keep sending vent commands!\n");
}

int currentFreq = 0;
unsigned long lastSwitch = 0;
int8_t noiseFloor = -110;
int spikeCount = 0;

void loop() {
    unsigned long now = millis();
    
    // Cycle frequency every 3 seconds
    if (now - lastSwitch >= 3000) {
        currentFreq = (currentFreq + 1) % NUM_FREQS;
        ELECHOUSE_cc1101.setMHZ(frequencies[currentFreq]);
        ELECHOUSE_cc1101.SetRx();
        delay(1);
        
        // Calibrate noise floor
        int32_t total = 0;
        for (int i = 0; i < 50; i++) {
            total += ELECHOUSE_cc1101.getRssi();
            delayMicroseconds(200);
        }
        noiseFloor = total / 50;
        
        Serial.printf("[%4lus] %.2f MHz (noise: %d dBm)\n",
                     now / 1000, frequencies[currentFreq], noiseFloor);
        lastSwitch = now;
    }
    
    // Fast RSSI sampling
    int8_t rssi = ELECHOUSE_cc1101.getRssi();
    
    // Trigger on signal 6 dB above noise
    if (rssi > noiseFloor + 6 && rssi > -95) {
        // Track the spike
        int8_t peak = rssi;
        unsigned long spikeStart = micros();
        int samples = 0;
        
        while (ELECHOUSE_cc1101.getRssi() > noiseFloor + 3) {
            int8_t r = ELECHOUSE_cc1101.getRssi();
            if (r > peak) peak = r;
            samples++;
            delayMicroseconds(50);
            if (samples > 2000) break; // Max 100ms
        }
        
        unsigned long duration = micros() - spikeStart;
        spikeCount++;
        
        Serial.printf("  *** SPIKE #%d @ %.2f MHz: peak=%d dBm, "
                      "dur=%lu us, samples=%d ***\n",
                     spikeCount, frequencies[currentFreq], 
                     peak, duration, samples);
    }
    
    delayMicroseconds(100); // ~10,000 samples/sec
}
