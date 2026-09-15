#include <Arduino.h>
#include <ELECHOUSE_CC1101_SRC_DRV.h>

#define CC1101_SCK  18
#define CC1101_MISO 19
#define CC1101_MOSI 23
#define CC1101_CS   5
#define CC1101_GDO0 22

int packetCount = 0;

void setup() {
    Serial.begin(115200);
    while (!Serial);
    
    ELECHOUSE_cc1101.setSpiPin(CC1101_SCK, CC1101_MISO, CC1101_MOSI, CC1101_CS);
    ELECHOUSE_cc1101.setGDO0(CC1101_GDO0);
    ELECHOUSE_cc1101.Init();
    
    if (!ELECHOUSE_cc1101.getCC1101()) {
        Serial.println("FAIL");
        while (true) delay(1000);
    }
    
    // Same config that produced structured data earlier
    ELECHOUSE_cc1101.setCCMode(1);
    ELECHOUSE_cc1101.setMHZ(915.00);
    ELECHOUSE_cc1101.setModulation(1);      // GFSK
    ELECHOUSE_cc1101.setDRate(38.38);
    ELECHOUSE_cc1101.setDeviation(47.60);
    ELECHOUSE_cc1101.setRxBW(325.00);
    ELECHOUSE_cc1101.setSyncMode(0);
    ELECHOUSE_cc1101.setCrc(false);
    ELECHOUSE_cc1101.setLengthConfig(0);
    ELECHOUSE_cc1101.setPacketLength(48);
    ELECHOUSE_cc1101.setManchester(false);
    ELECHOUSE_cc1101.setAppendStatus(true);
    ELECHOUSE_cc1101.setPQT(0);
    ELECHOUSE_cc1101.SetRx();
    
    // CSV header
    Serial.println("phase,ts_ms,rssi,lqi,hex");
}

void loop() {
    unsigned long now = millis();
    
    // Phase tracking: 0-60s = BASELINE, 60-120s = COMMANDS
    const char* phase = (now < 60000) ? "BASE" : "CMD";
    
    // Print phase transitions
    static bool phaseAnnounced = false;
    if (now >= 60000 && !phaseAnnounced) {
        Serial.println("# === PHASE CHANGE: SEND COMMANDS NOW ===");
        phaseAnnounced = true;
    }
    
    byte rxbytes = ELECHOUSE_cc1101.SpiReadStatus(CC1101_RXBYTES);
    if (rxbytes & 0x80) {
        ELECHOUSE_cc1101.setSidle();
        ELECHOUSE_cc1101.SpiStrobe(CC1101_SFRX);
        ELECHOUSE_cc1101.SetRx();
        return;
    }
    rxbytes &= 0x7F;
    
    if (rxbytes >= 50) {
        byte buffer[50];
        ELECHOUSE_cc1101.SpiReadBurstReg(CC1101_RXFIFO, buffer, 50);
        
        int8_t pkt_rssi;
        uint8_t raw_rssi = buffer[48];
        if (raw_rssi >= 128) pkt_rssi = ((int16_t)raw_rssi - 256) / 2 - 74;
        else pkt_rssi = raw_rssi / 2 - 74;
        uint8_t lqi = buffer[49] & 0x7F;
        
        if (pkt_rssi > -85) {
            packetCount++;
            Serial.printf("%s,%lu,%d,%d,", phase, now, pkt_rssi, lqi);
            for (int i = 0; i < 48; i++) Serial.printf("%02X", buffer[i]);
            Serial.println();
        }
        
        ELECHOUSE_cc1101.setSidle();
        ELECHOUSE_cc1101.SpiStrobe(CC1101_SFRX);
        ELECHOUSE_cc1101.SetRx();
    }
    
    delayMicroseconds(500);
}
