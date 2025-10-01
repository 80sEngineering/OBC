import ht16k33_driver
import time
from button import Button
from machine import Pin, I2C

i2c = I2C(id=1, sda=Pin(2), scl=Pin(3), freq = 9600)
display = ht16k33_driver.Seg14x4(i2c)
latch = Pin(0, Pin.OUT)
latch.high() 

def button_manager(button_id, long_press):
    display.put_text(str(button_id))
    display.show()
    time.sleep_ms(200)
    
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

while True:
    display.clear()
    display.show()
    time.sleep(0.1)