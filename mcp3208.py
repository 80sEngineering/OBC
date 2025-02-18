import machine
import time

class MCP3208:
    def __init__(self, spi, cs):
        self.cs = cs
        self.cs.value(1) # ncs on
        self._spi = spi
    
    def read_value(self, pin):
        cmd = 128  # 1000 0000
        cmd += 64  # 1100 0000
        cmd += ((pin & 0x07) << 3)
        config_bits = bytearray([cmd,0x00,0x00])
        response = bytearray(3)
        self.cs.value(0) 
        self._spi.write_readinto(config_bits, response)
        self.cs.value(1)
        adc_value = (response[0] & 0x01) << 11  # only B11 is here
        adc_value |= response[1] << 3           # B10:B3
        adc_value |= response[2] >> 5           # MSB has B2:B0 ... need to move down to LSB
        return adc_value
    
    def read_voltage(self,pin):
        adc_value = self.read_value(pin)
        voltage_value = 5.2 * adc_value / 4096
        return voltage_value
        