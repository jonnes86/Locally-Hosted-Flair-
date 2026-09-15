#include "cc1101.h"
#include <math.h>

#define FXOSC 26000000.0 // 26 MHz crystal

CC1101::CC1101(int8_t cs_pin, int8_t gdo0_pin, int8_t gdo2_pin) {
    _cs_pin = cs_pin;
    _gdo0_pin = gdo0_pin;
    _gdo2_pin = gdo2_pin;
}

bool CC1101::init() {
    pinMode(_cs_pin, OUTPUT);
    digitalWrite(_cs_pin, HIGH);
    pinMode(_gdo0_pin, INPUT);
    if (_gdo2_pin >= 0) {
        pinMode(_gdo2_pin, INPUT);
    }

    // Explicitly set SPI pins for ESP32
    SPI.begin(18, 19, 23, _cs_pin);  // SCK, MISO, MOSI, SS
    SPI.setFrequency(1000000);  // 1 MHz SPI clock (conservative)
    SPI.setBitOrder(MSBFIRST);
    SPI.setDataMode(SPI_MODE0);

    Serial.println("SPI initialized, resetting CC1101...");
    reset();
    delay(100);

    // Verify SPI connection by reading version register
    // CC1101 version should be 0x14 (decimal 20)
    uint8_t partnum = readReg(CC1101_PARTNUM | CC1101_READ_BURST);
    uint8_t version = readReg(CC1101_VERSION | CC1101_READ_BURST);
    Serial.printf("CC1101 PARTNUM: 0x%02X, VERSION: 0x%02X\n", partnum, version);

    if (version == 0x00 || version == 0xFF) {
        Serial.println("ERROR: CC1101 not responding on SPI.");
        Serial.println("Check wiring:");
        Serial.printf("  CS  = GPIO %d\n", _cs_pin);
        Serial.printf("  GDO0= GPIO %d\n", _gdo0_pin);
        Serial.println("  SCK = GPIO 18");
        Serial.println("  MOSI= GPIO 23");
        Serial.println("  MISO= GPIO 19");
        Serial.println("  VCC = 3.3V (NOT 5V!)");
        Serial.println("  GND = GND");
        return false;
    }

    Serial.printf("CC1101 detected! (version 0x%02X)\n", version);

    // Default Configuration
    writeReg(CC1101_IOCFG2, 0x29);
    writeReg(CC1101_IOCFG1, 0x2E);
    writeReg(CC1101_IOCFG0, 0x06);
    writeReg(CC1101_FIFOTHR, 0x47);
    writeReg(CC1101_PKTCTRL1, 0x04); // Append status (RSSI, LQI)
    writeReg(CC1101_PKTCTRL0, 0x05); // Variable packet length, CRC enabled
    writeReg(CC1101_MCSM1, 0x30);    // Return to IDLE after packet
    writeReg(CC1101_MCSM0, 0x18);
    writeReg(CC1101_FOCCFG, 0x16);
    writeReg(CC1101_BSCFG, 0x6C);
    writeReg(CC1101_AGCCTRL2, 0x43);
    writeReg(CC1101_AGCCTRL1, 0x40);
    writeReg(CC1101_AGCCTRL0, 0x91);
    writeReg(CC1101_FREND1, 0x56);
    writeReg(CC1101_FREND0, 0x10);
    writeReg(CC1101_FSCAL3, 0xE9);
    writeReg(CC1101_FSCAL2, 0x2A);
    writeReg(CC1101_FSCAL1, 0x00);
    writeReg(CC1101_FSCAL0, 0x1F);
    writeReg(CC1101_TEST2, 0x81);
    writeReg(CC1101_TEST1, 0x35);
    writeReg(CC1101_TEST0, 0x09);

    return true;
}


void CC1101::reset() {
    digitalWrite(_cs_pin, LOW);
    delay(1);
    digitalWrite(_cs_pin, HIGH);
    delay(1);
    digitalWrite(_cs_pin, LOW);
    // Wait for MISO (SO) to go low, with timeout
    unsigned long timeout = millis() + 100;
    while (digitalRead(19) == HIGH) {
        if (millis() > timeout) {
            Serial.println("WARNING: MISO timeout during reset");
            break;
        }
    }
    writeStrobe(CC1101_SRES);
    timeout = millis() + 100;
    while (digitalRead(19) == HIGH) {
        if (millis() > timeout) {
            Serial.println("WARNING: MISO timeout after SRES");
            break;
        }
    }
    digitalWrite(_cs_pin, HIGH);
}


void CC1101::setFrequency(float mhz) {
    _freq = mhz;
    uint32_t freq_reg = (uint32_t)((mhz * 1000000.0) / (FXOSC / 65536.0));
    writeReg(CC1101_FREQ2, (freq_reg >> 16) & 0xFF);
    writeReg(CC1101_FREQ1, (freq_reg >> 8) & 0xFF);
    writeReg(CC1101_FREQ0, freq_reg & 0xFF);
}

void CC1101::setDataRate(float kbps) {
    _rate = kbps;
    float drate_hz = kbps * 1000.0;
    uint8_t e = 0;
    uint32_t m = 0;
    
    // Formula: R_DATA = (256 + DRATE_M) * 2^DRATE_E * (f_XOSC / 2^28)
    // Finding E and M
    for (e = 0; e < 16; e++) {
        m = (uint32_t)((drate_hz * 268435456.0) / (FXOSC * pow(2, e)) - 256.0 + 0.5);
        if (m < 256) {
            break;
        }
    }
    
    uint8_t mdmcfg4 = readReg(CC1101_MDMCFG4) & 0xF0;
    mdmcfg4 |= (e & 0x0F);
    writeReg(CC1101_MDMCFG4, mdmcfg4);
    writeReg(CC1101_MDMCFG3, m & 0xFF);
}

void CC1101::setModulation(Modulation mod) {
    _mod = mod;
    uint8_t mdmcfg2 = readReg(CC1101_MDMCFG2) & 0x8F;
    mdmcfg2 |= mod;
    writeReg(CC1101_MDMCFG2, mdmcfg2);
}

void CC1101::setDeviation(float khz) {
    _dev = khz;
    float dev_hz = khz * 1000.0;
    uint8_t e = 0;
    uint8_t m = 0;
    
    // Formula: f_dev = (f_XOSC / 2^17) * (8 + DEVIATION_M) * 2^DEVIATION_E
    for (e = 0; e < 8; e++) {
        m = (uint8_t)((dev_hz * 131072.0) / (FXOSC * pow(2, e)) - 8.0 + 0.5);
        if (m < 8) {
            break;
        }
    }
    
    writeReg(CC1101_DEVIATN, ((e & 0x07) << 4) | (m & 0x07));
}

void CC1101::setSyncWord(uint16_t sync) {
    _sync = sync;
    writeReg(CC1101_SYNC1, (sync >> 8) & 0xFF);
    writeReg(CC1101_SYNC0, sync & 0xFF);
    
    // Configure sync word detection
    uint8_t mdmcfg2 = readReg(CC1101_MDMCFG2) & 0xF8;
    if (sync == 0x0000) {
        mdmcfg2 |= 0x00; // No preamble/sync
    } else {
        mdmcfg2 |= 0x02; // 16/16 sync word bits detected
    }
    writeReg(CC1101_MDMCFG2, mdmcfg2);
}

void CC1101::setPreambleLen(int bytes) {
    uint8_t num_preamble = 0;
    if (bytes <= 2) num_preamble = 0;
    else if (bytes <= 3) num_preamble = 1;
    else if (bytes <= 4) num_preamble = 2;
    else if (bytes <= 6) num_preamble = 3;
    else if (bytes <= 8) num_preamble = 4;
    else if (bytes <= 12) num_preamble = 5;
    else if (bytes <= 16) num_preamble = 6;
    else num_preamble = 7;
    
    uint8_t mdmcfg1 = readReg(CC1101_MDMCFG1) & 0x8F;
    mdmcfg1 |= (num_preamble << 4);
    writeReg(CC1101_MDMCFG1, mdmcfg1);
}

void CC1101::setRxBandwidth(float khz) {
    float bw_hz = khz * 1000.0;
    uint8_t e = 0;
    uint8_t m = 0;
    
    // Formula: BW = f_XOSC / (8 * (4 + CHANBW_M) * 2^CHANBW_E)
    for (e = 0; e < 4; e++) {
        for (m = 0; m < 4; m++) {
            float calc_bw = FXOSC / (8.0 * (4 + m) * pow(2, e));
            if (calc_bw <= bw_hz * 1.1) { // Allow some margin
                goto done;
            }
        }
    }
done:
    uint8_t mdmcfg4 = readReg(CC1101_MDMCFG4) & 0x0F;
    mdmcfg4 |= ((e & 0x03) << 6) | ((m & 0x03) << 4);
    writeReg(CC1101_MDMCFG4, mdmcfg4);
}

void CC1101::setManchester(bool enable) {
    _manch = enable;
    uint8_t mdmcfg2 = readReg(CC1101_MDMCFG2) & 0xF7;
    if (enable) mdmcfg2 |= 0x08;
    writeReg(CC1101_MDMCFG2, mdmcfg2);
}

void CC1101::startRx() {
    writeStrobe(CC1101_SIDLE);
    writeStrobe(CC1101_SFRX);
    writeStrobe(CC1101_SRX);
}

int8_t CC1101::getRSSI() {
    uint8_t rssi_dec = readReg(CC1101_RSSI | CC1101_READ_BURST);
    int8_t rssi_dbm;
    if (rssi_dec >= 128) {
        rssi_dbm = (int16_t)((int16_t)(rssi_dec - 256) / 2) - 74;
    } else {
        rssi_dbm = (rssi_dec / 2) - 74;
    }
    return rssi_dbm;
}

uint8_t CC1101::getLQI() {
    return readReg(CC1101_LQI | CC1101_READ_BURST) & 0x7F;
}

bool CC1101::receivePacket(uint8_t* buffer, uint8_t* length) {
    if (digitalRead(_gdo0_pin) == HIGH) {
        uint8_t bytes_in_fifo = readReg(CC1101_RXBYTES | CC1101_READ_BURST) & 0x7F;
        if (bytes_in_fifo > 0) {
            uint8_t pkt_len = readReg(CC1101_RXFIFO); // Variable length assumed
            
            if (pkt_len <= *length) {
                readBurst(CC1101_RXFIFO, buffer, pkt_len);
                uint8_t status[2];
                readBurst(CC1101_RXFIFO, status, 2); // Read appended status (RSSI, LQI/CRC_OK)
                
                *length = pkt_len;
                bool crc_ok = (status[1] & 0x80) != 0;
                
                writeStrobe(CC1101_SIDLE);
                writeStrobe(CC1101_SFRX);
                writeStrobe(CC1101_SRX);
                
                return crc_ok;
            } else {
                // Overflow or too large packet
                *length = pkt_len;
                writeStrobe(CC1101_SIDLE);
                writeStrobe(CC1101_SFRX);
                writeStrobe(CC1101_SRX);
                return false;
            }
        }
    }
    return false;
}

uint8_t CC1101::readReg(uint8_t addr) {
    digitalWrite(_cs_pin, LOW);
    SPI.transfer(addr | CC1101_READ_SINGLE);
    uint8_t val = SPI.transfer(0x00);
    digitalWrite(_cs_pin, HIGH);
    return val;
}

void CC1101::writeReg(uint8_t addr, uint8_t value) {
    digitalWrite(_cs_pin, LOW);
    SPI.transfer(addr);
    SPI.transfer(value);
    digitalWrite(_cs_pin, HIGH);
}

void CC1101::writeBurst(uint8_t addr, uint8_t* buffer, uint8_t size) {
    digitalWrite(_cs_pin, LOW);
    SPI.transfer(addr | CC1101_WRITE_BURST);
    for (uint8_t i = 0; i < size; i++) {
        SPI.transfer(buffer[i]);
    }
    digitalWrite(_cs_pin, HIGH);
}

void CC1101::readBurst(uint8_t addr, uint8_t* buffer, uint8_t size) {
    digitalWrite(_cs_pin, LOW);
    SPI.transfer(addr | CC1101_READ_BURST);
    for (uint8_t i = 0; i < size; i++) {
        buffer[i] = SPI.transfer(0x00);
    }
    digitalWrite(_cs_pin, HIGH);
}

uint8_t CC1101::writeStrobe(uint8_t strobe) {
    digitalWrite(_cs_pin, LOW);
    uint8_t status = SPI.transfer(strobe);
    digitalWrite(_cs_pin, HIGH);
    return status;
}
