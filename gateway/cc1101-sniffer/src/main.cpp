#include <Arduino.h>
#include <ELECHOUSE_CC1101_SRC_DRV.h>

#define CC1101_SCK  18
#define CC1101_MISO 19
#define CC1101_MOSI 23
#define CC1101_CS   5
#define CC1101_GDO0 27

#define BUF_SIZE 384
uint8_t bitBuffer[BUF_SIZE];
int captureCount = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial);
    
    Serial.println("=== Single-Channel Stakeout @ 907.47 MHz ===");
    
    ELECHOUSE_cc1101.setSpiPin(CC1101_SCK, CC1101_MISO, CC1101_MOSI, CC1101_CS);
    ELECHOUSE_cc1101.setGDO0(CC1101_GDO0);
    ELECHOUSE_cc1101.Init();
    
    if (!ELECHOUSE_cc1101.getCC1101()) {
        Serial.println("FAIL");
        while (true) delay(1000);
    }
    
    // Async serial mode on 907.47 MHz
    ELECHOUSE_cc1101.setSidle();
    ELECHOUSE_cc1101.setMHZ(907.47);
    ELECHOUSE_cc1101.setModulation(1);      // GFSK
    ELECHOUSE_cc1101.setDRate(38.38);
    ELECHOUSE_cc1101.setDeviation(47.60);
    ELECHOUSE_cc1101.setRxBW(325.00);
    ELECHOUSE_cc1101.setDcFilterOff(false);
    ELECHOUSE_cc1101.setManchester(false);
    ELECHOUSE_cc1101.setCCMode(0);
    ELECHOUSE_cc1101.SpiWriteReg(CC1101_IOCFG0, 0x0D);
    ELECHOUSE_cc1101.SpiWriteReg(0x08, 0x30);
    ELECHOUSE_cc1101.SetRx();
    
    pinMode(CC1101_GDO0, INPUT);
    
    Serial.println("Parked on 907.47 MHz - waiting for Flair packets");
    Serial.println("RSSI checked every 100us, threshold -92 dBm");
    Serial.println("SEND VENT COMMANDS!\n");
}

void loop() {
    int rssi = ELECHOUSE_cc1101.getRssi();
    
    // Very sensitive threshold for brief packets
    if (rssi > -92) {
        // Immediately capture bitstream
        for (int i = 0; i < BUF_SIZE; i++) {
            uint8_t byte_val = 0;
            for (int bit = 7; bit >= 0; bit--) {
                byte_val |= (digitalRead(CC1101_GDO0) << bit);
                delayMicroseconds(13);  // ~77 kHz = 2x oversample of 38.4k
            }
            bitBuffer[i] = byte_val;
        }
        
        int finalRssi = ELECHOUSE_cc1101.getRssi();
        
        // Check for preamble (0xAA/0x55)
        int preambleCount = 0, preambleStart = -1;
        for (int i = 0; i < BUF_SIZE; i++) {
            if (bitBuffer[i] == 0xAA || bitBuffer[i] == 0x55) {
                preambleCount++;
                if (preambleStart < 0) preambleStart = i;
            }
        }
        
        // Check for non-trivial content
        int nonFF = 0, nonZero = 0, transitions = 0;
        for (int i = 0; i < BUF_SIZE; i++) {
            if (bitBuffer[i] != 0xFF) nonFF++;
            if (bitBuffer[i] != 0x00) nonZero++;
            if (i > 0 && bitBuffer[i] != bitBuffer[i-1]) transitions++;
        }
        
        captureCount++;
        
        // Print everything - we need to see ALL captures
        Serial.printf("\n#%d t=%lus RSSI:%d->%d preamble:%d trans:%d nFF:%d nZ:%d\n",
                     captureCount, millis()/1000, rssi, finalRssi, 
                     preambleCount, transitions, nonFF, nonZero);
        
        // Only dump hex if interesting
        if (preambleCount >= 2 || transitions > 30) {
            for (int i = 0; i < BUF_SIZE; i += 16) {
                Serial.printf("%3d: ", i);
                for (int j = 0; j < 16 && (i+j) < BUF_SIZE; j++)
                    Serial.printf("%02X ", bitBuffer[i+j]);
                Serial.println();
            }
            
            if (preambleStart >= 0) {
                int end = preambleStart;
                while (end < BUF_SIZE && (bitBuffer[end] == 0xAA || bitBuffer[end] == 0x55)) end++;
                Serial.printf(">>> PREAMBLE %d-%d, SYNC+DATA: ", preambleStart, end-1);
                for (int i = end; i < min(end + 24, (int)BUF_SIZE); i++)
                    Serial.printf("%02X ", bitBuffer[i]);
                Serial.println("<<<");
            }
        }
        
        // Brief cooldown to avoid re-triggering on same signal
        delay(50);
    }
    
    delayMicroseconds(100);
}
