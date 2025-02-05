from machine import Pin
import time 
import logging

class Button:
    def __init__(self, pin_number, button_id, function):
        self.button_id = button_id
        if self.button_id != 9:
            self.pin = Pin(pin_number, Pin.IN, Pin.PULL_UP)
        else:
            self.pin = Pin(pin_number, Pin.IN, Pin.PULL_DOWN)
        self.function = function
        self.current_press = {'pressure':None,'release':None}
        self.long_press = False
        self.pin.irq(handler=lambda f: self.debounce(), trigger = Pin.IRQ_RISING | Pin.IRQ_FALLING)

    def debounce(self):
        current = time.ticks_ms()
            
        if self.pin.value() == (self.button_id == 9): #RISING
            self.current_press['pressure'] = current
        else: #FALLING
            if time.ticks_diff(current, self.current_press['release']) > 200:
                logging.info(f"> Pressed button: {self.button_id}")
                self.current_press['release'] = current
                self.check_for_long_press()
                self.function(self.button_id,self.long_press)
   
    def check_for_long_press(self):
        if time.ticks_diff(self.current_press['release'],self.current_press['pressure'])>700:
            self.long_press = True
        else:
            self.long_press = False
            
            
        