#include <Arduino.h>
#include <ELECHOUSE_CC1101_SRC_DRV.h>

#define CC1101_SCK  18
#define CC1101_MISO 19
#define CC1101_MOSI 23
#define CC1101_CS   5
#define CC1101_GDO0 22

int packetCount = 0;

// Try multiple configs to find cleanest demodulation
struct Config {
    float freq;
    byte mod;       // 0=2-FSK, 1=GFSK
    float drate;
    float dev;
    bool manchester;
    const char* label;
};

Config configs[] = {
    {915.00, 0, 38.38, 47.60, false, "915.00 2FSK 38.4k dev47"},
    {915.00, 1, 38.38, 47.60, false, "915.00 GFSK 38.4k dev47"},
    {915.00, 0, 38.38, 47.60, true,  "915.00 2FSK 38.4k dev47 MANCH"},
    {915.00, 1, 38.38, 47.60, true,  "915.00 GFSK 38.4k dev47 MANCH"},
    {915.00, 0, 100.0, 47.60, false, "915.00 2FSK 100k dev47"},
    {915.00, 1, 100.0, 47.60, false, "915.00 GFSK 100k dev47"},
    {915.00, 0, 50.0,  47.60, false, "915.00 2FSK 50k dev47"},
    {915.00, 1, 50.0,  47.60, false, "915.00 GFSK 50k dev47"},
};
const int NUM_CONFIGS = 8;
int currentConfig = 0;
unsigned long configStartTime = 0;

void applyConfig(int idx) {
    ELECHOUSE_cc1101.setSidle();
    ELECHOUSE_cc1101.setMHZ(configs[idx].freq);
    ELECHOUSE_cc1101.setModulation(configs[idx].mod);
    ELECHOUSE_cc1101.setDRate(configs[idx].drate);
    ELECHOUSE_cc1101.setDeviation(configs[idx].dev);
    ELECHOUSE_cc1101.setManchester(configs[idx].manchester);
    ELECHOUSE_cc1101.setRxBW(325.00);
    ELECHOUSE_cc1101.setCCMode(1);
    ELECHOUSE_cc1101.setSyncMode(0);
    ELECHOUSE_cc1101.setCrc(false);
    ELECHOUSE_cc1101.setLengthConfig(0);
    ELECHOUSE_cc1101.setPacketLength(48);  // Longer packet for more data
    ELECHOUSE_cc1101.setAppendStatus(true);
    ELECHOUSE_cc1101.setPQT(0);
    ELECHOUSE_cc1101.SpiStrobe(CC1101_SFRX);
    ELECHOUSE_cc1101.SetRx();
}

void setup() {
    Serial.begin(115200);
    while (!Serial);
    
    Serial.println("=== Flair Packet Logger ===");
    Serial.println("FORMAT: timestamp_ms,config,rssi,lqi,crc,hex_data");
    Serial.println("Open vent in 10s, close in 40s");
    Serial.println();
    
    ELECHOUSE_cc1101.setSpiPin(CC1101_SCK, CC1101_MISO, CC1101_MOSI, CC1101_CS);
    ELECHOUSE_cc1101.setGDO0(CC1101_GDO0);
    ELECHOUSE_cc1101.Init();
    
    if (!ELECHOUSE_cc1101.getCC1101()) {
        Serial.println("CC1101 FAIL");
        while (true) delay(1000);
    }
    
    applyConfig(0);
    Serial.printf("CONFIG: %s\n\n", configs[0].label);
    configStartTime = millis();
}

void loop() {
    unsigned long now = millis();
    
    // Switch config every 15 seconds
    if (now - configStartTime >= 15000) {
        currentConfig = (currentConfig + 1) % NUM_CONFIGS;
        applyConfig(currentConfig);
        Serial.printf("\n--- CONFIG: %s ---\n", configs[currentConfig].label);
        configStartTime = now;
    }
    
    // Check FIFO
    byte rxbytes = ELECHOUSE_cc1101.SpiReadStatus(CC1101_RXBYTES);
    bool overflow = rxbytes & 0x80;
    rxbytes &= 0x7F;
    
    if (overflow) {
        ELECHOUSE_cc1101.setSidle();
        ELECHOUSE_cc1101.SpiStrobe(CC1101_SFRX);
        ELECHOUSE_cc1101.SetRx();
        return;
    }
    
    if (rxbytes >= 50) {  // 48 data + 2 status
        byte buffer[50];
        ELECHOUSE_cc1101.SpiReadBurstReg(CC1101_RXFIFO, buffer, 50);
        
        // Parse appended status
        int8_t pkt_rssi;
        uint8_t raw_rssi = buffer[48];
        if (raw_rssi >= 128) pkt_rssi = ((int16_t)raw_rssi - 256) / 2 - 74;
        else pkt_rssi = raw_rssi / 2 - 74;
        
        bool crc_ok = buffer[49] & 0x80;
        uint8_t lqi = buffer[49] & 0x7F;
        
        // Only log packets with real signal (RSSI > -85)
        if (pkt_rssi > -85) {
            packetCount++;
            
            // CSV format for easy parsing
            Serial.printf("%lu,%d,%d,%d,%d,", now, currentConfig, pkt_rssi, lqi, crc_ok ? 1 : 0);
            for (int i = 0; i < 48; i++) {
                Serial.printf("%02X", buffer[i]);
            }
            Serial.println();
        }
        
        ELECHOUSE_cc1101.setSidle();
        ELECHOUSE_cc1101.SpiStrobe(CC1101_SFRX);
        ELECHOUSE_cc1101.SetRx();
    }
    
    delayMicroseconds(500);
}
