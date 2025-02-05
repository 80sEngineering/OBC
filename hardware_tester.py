import ht16k33_driver
import time
from button import Button
from machine import Pin, I2C, SPI
from imu import MPU6050
from ds3231 import DS3231
from mcp3208 import MCP3208

i2c = I2C(id=1, sda=Pin(2), scl=Pin(3), freq = 9600)
display = ht16k33_driver.Seg14x4(i2c)
display.fill()
latch = Pin(0, Pin.OUT)
latch.high()
mpu = MPU6050(i2c, device_addr = 1)
ds = DS3231(i2c)
cs_spi = Pin(17, Pin.OUT)
spi = SPI(0, sck=Pin(18),mosi=Pin(19),miso=Pin(16), baudrate=50000)
adc = MCP3008(spi, cs_spi)


def button_manager(button_id, long_press):
    display.put_text(str(button_id))
    display.show()
    time.sleep_ms(500)
    
button1 = Button(4, 1, button_manager)
button2 = Button(5, 2, button_manager)
button3 = Button(6, 3, button_manager)
button4 = Button(7, 4, button_manager)
button5 = Button(8, 5, button_manager)
button6 = Button(9, 6, button_manager)
button7 = Button(10, 7, button_manager)
button8 = Button(11, 8, button_manager)
button9 = Button(12, 9, button_manager)
button10 = Button(13, 10, button_manager)
button11 = Button(14, 11, button_manager)
button12 = Button(15, 12, button_manager)
button13 = Button(20, 13, button_manager)
led = Pin(15,Pin.OUT)
led.toggle()

year = 2024 # Can be yyyy or yy format
month = 11
mday = 27
hour = 18 # 24 hour format only
minute = 03
second = 30 # Optional
weekday = 3 # Optional

datetime = (year, month, mday, hour, minute, second, weekday)
ds.datetime(datetime)


while True:
    display.clear()
    display.show()
    adc_voltage = adc.read_voltage(2)
    print(adc_voltage * 3)
    time.sleep(0.1)