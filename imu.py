from utime import sleep_ms
from machine import I2C
from vector3d import Vector3d


class MPUException(OSError):
    '''
    Exception for MPU devices
    '''
    pass


def bytes_toint(msb, lsb):
    '''
    Convert two bytes to signed integer (big endian)
    for little endian reverse msb, lsb arguments
    Can be used in an interrupt handler
    '''
    if not msb & 0x80:
        return msb << 8 | lsb  # +ve
    return - (((msb ^ 255) << 8) | (lsb ^ 255) + 1)


class MPU6050(object):
    '''
    Module for InvenSense IMUs. Base class implements MPU6050 6DOF sensor, with
    features common to MPU9150 and MPU9250 9DOF sensors.
    '''
    
    def __init__(self, side_str, device_addr=None, transposition=(0, 1, 2), scaling=(1, 1, 1)):

        self._accel = Vector3d(transposition, scaling, self._accel_callback)
        self.buf1 = bytearray(1)                # Pre-allocated buffers for reads: allows reads to
        self.buf2 = bytearray(2)                # be done in interrupt handlers
        self.buf3 = bytearray(3)
        self.buf6 = bytearray(6)

        self._mpu_i2c = side_str
        self.mpu_addr = 105

        self.wake()                             # wake it up
        self.accel_range = 0                    # default to highest sensitivity


    # read from device
    def _read(self, buf, memaddr, addr):        # addr = I2C device address, memaddr = memory location within the I2C device
        '''
        Read bytes to pre-allocated buffer Caller traps OSError.
        '''
        self._mpu_i2c.readfrom_mem_into(addr, memaddr, buf)

    # write to device
    def _write(self, data, memaddr, addr):
        '''
        Perform a memory write. Caller should trap OSError.
        '''
        self.buf1[0] = data
        self._mpu_i2c.writeto_mem(addr, memaddr, self.buf1)

    # wake
    def wake(self):
        '''
        Wakes the device.
        '''
        try:
            self._write(0x01, 0x6B, self.mpu_addr)  # Use best clock source
        except OSError:
            raise MPUException(self._I2Cerror)
        return 'awake'

    def sensors(self):
        '''
        returns sensor objects accel, gyro
        '''
        return self._accel, self._gyro

    # accelerometer range
    @property
    def accel_range(self):
        '''
        Accelerometer range
        Value:              0   1   2   3
        for range +/-:      2   4   8   16  g
        '''
        self._read(self.buf1, 0x1C, self.mpu_addr)
        ari = self.buf1[0]//8
        return ari

    @accel_range.setter
    def accel_range(self, accel_range):
        '''
        Set accelerometer range
        Pass:               0   1   2   3
        for range +/-:      2   4   8   16  g
        '''
        ar_bytes = (0x00, 0x08, 0x10, 0x18)
        if accel_range in range(len(ar_bytes)):
            try:
                self._write(ar_bytes[accel_range], 0x1C, self.mpu_addr)
            except OSError:
                raise MPUException(self._I2Cerror)
        else:
            raise ValueError('accel_range can only be 0, 1, 2 or 3')


    # Accelerometer
    @property
    def accel(self):
        '''
        Acceleremoter object
        '''
        return self._accel

    def _accel_callback(self):
        '''
        Update accelerometer Vector3d object
        '''
        try:
            self._read(self.buf6, 0x3B, self.mpu_addr)
        except OSError:
            raise MPUException(self._I2Cerror)
        self._accel._ivector[0] = bytes_toint(self.buf6[0], self.buf6[1])
        self._accel._ivector[1] = bytes_toint(self.buf6[2], self.buf6[3])
        self._accel._ivector[2] = bytes_toint(self.buf6[4], self.buf6[5])
        scale = (16384, 8192, 4096, 2048)
        self._accel._vector[0] = self._accel._ivector[0]/scale[self.accel_range]
        self._accel._vector[1] = self._accel._ivector[1]/scale[self.accel_range]
        self._accel._vector[2] = self._accel._ivector[2]/scale[self.accel_range]
