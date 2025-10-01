#! /usr/bin/env micropython

# Micropython driver for the DS3231 RTC Module

# Inspiration from work done by Mike Causer (mcauser) for the DS1307
# https://github.com/mcauser/micropython-tinyrtc-i2c/blob/master/ds1307.py

# The MIT License (MIT)
#
# Copyright (c) 2020 Willem Peterse
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from micropython import const
import logging

DATETIME_REG    = const(0) # 7 bytes
ALARM1_REG      = const(7) # 5 bytes
ALARM2_REG      = const(11) # 4 bytes
CONTROL_REG     = const(14)
STATUS_REG      = const(15)
AGING_REG       = const(16)
TEMPERATURE_REG = const(17) # 2 bytes

def dectobcd(decimal):
    """Convert decimal to binary coded decimal (BCD) format"""
    return (decimal // 10) << 4 | (decimal % 10)

def bcdtodec(bcd):
    """Convert binary coded decimal to decimal"""
    return ((bcd >> 4) * 10) + (bcd & 0x0F)


class DS3231:
    """ DS3231 RTC driver.

    Hard coded to work with year 2000-2099."""
    FREQ_1      = const(1)
    FREQ_1024   = const(2)
    FREQ_4096   = const(3)
    FREQ_8192   = const(4)
    SQW_32K     = const(1)


    def __init__(self, i2c, addr=0x68):
        self.i2c = i2c
        self.addr = addr
        self._timebuf = bytearray(7) # Pre-allocate a buffer for the time data
        self._buf = bytearray(1) # Pre-allocate a single bytearray for re-use
        self._al1_buf = bytearray(4)
        self._al2buf = bytearray(3)

    def datetime(self, datetime=None):
        """Get or set datetime

        Always sets or returns in 24h format, converts to 24h if clock is set to 12h format
        datetime : tuple, (0-year, 1-month, 2-day, 3-hour, 4-minutes[, 5-seconds[, 6-weekday]])"""
        if datetime is None:
            try:
                self.i2c.readfrom_mem_into(self.addr, DATETIME_REG, self._timebuf)
            except OSError:
                return (2025, 1, 1, 1, 0, 0, 1, 0)
            # 0x00 - Seconds    BCD
            # 0x01 - Minutes    BCD
            # 0x02 - Hour       0 12/24 AM/PM/20s BCD
            # 0x03 - WDay 1-7   0000 0 BCD
            # 0x04 - Day 1-31   00 BCD
            # 0x05 - Month 1-12 Century 00 BCD
            # 0x06 - Year 0-99  BCD (2000-2099)
            seconds = bcdtodec(self._timebuf[0])
            minutes = bcdtodec(self._timebuf[1])
            
            if (self._timebuf[2] & 0x40) >> 6: # Check for 12 hour mode bit
                hour = bcdtodec(self._timebuf[2] & 0x9f) # Mask out bit 6(12/24) and 5(AM/PM)
                if (self._timebuf[2] & 0x20) >> 5: # bit 5(AM/PM)
                    # PM
                    hour += 12
            else:
                # 24h mode
                hour = bcdtodec(self._timebuf[2] & 0xbf) # Mask bit 6 (12/24 format)

            weekday = bcdtodec(self._timebuf[3]) # Can be set arbitrarily by user (1,7)
            day = bcdtodec(self._timebuf[4])
            month = bcdtodec(self._timebuf[5] & 0x7f) # Mask out the century bit
            year = bcdtodec(self._timebuf[6]) + 2000

            if self.OSF():
                logging.warn(" > WARNING: Oscillator stop flag set. Time may not be accurate.")
                self._OSF_reset()
                
            return (year, month, day, weekday, hour, minutes, seconds, 0) # Conforms to the ESP8266 RTC (v1.13)

        # Set the clock
        try:
            self._timebuf[3] = dectobcd(datetime[6]) # Day of week
        except IndexError:
            self._timebuf[3] = 0
        try:
            self._timebuf[0] = dectobcd(datetime[5]) # Seconds
        except IndexError:
            self._timebuf[0] = 0
        self._timebuf[1] = dectobcd(datetime[4]) # Minutes
        self._timebuf[2] = dectobcd(datetime[3]) # Hour + the 24h format flag
        self._timebuf[4] = dectobcd(datetime[2]) # Day
        self._timebuf[5] = dectobcd(datetime[1]) & 0xff # Month + mask the century flag
        self._timebuf[6] = dectobcd(int(str(datetime[0])[-2:])) # Year can be yyyy, or yy
        self.i2c.writeto_mem(self.addr, DATETIME_REG, self._timebuf)
        self._OSF_reset()
        return True


    def OSF(self):
        """Returns the oscillator stop flag (OSF).

        1 indicates that the oscillator is stopped or was stopped for some
        period in the past and may be used to judge the validity of
        the time data.
        returns : bool"""
        return bool(self.i2c.readfrom_mem(self.addr, STATUS_REG, 1)[0] >> 7)

    def _OSF_reset(self):
        """Clear the oscillator stop flag (OSF)"""
        self.i2c.readfrom_mem_into(self.addr, STATUS_REG, self._buf)
        self.i2c.writeto_mem(self.addr, STATUS_REG, bytearray([self._buf[0] & 0x7f]))

    def _is_busy(self):
        """Returns True when device is busy doing TCXO management"""
        return bool(self.i2c.readfrom_mem(self.addr, STATUS_REG, 1)[0] & (1 << 2))