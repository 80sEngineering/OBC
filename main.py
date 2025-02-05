# -----------------------------------------------------------------------------
# 80s Engineering On-board Computer Firmware v0.1
# Copyright (C) 2024 80s Engineering. All rights reserved.
#
# This firmware is proprietary. Users are permitted to modify it; however,
# redistribution, selling, or unauthorized commercial use is not authorized.
#
# For inquiries, support, or permission requests, please contact us at:
# contact@80s.engineering
#
# THE FIRMWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE FIRMWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# -----------------------------------------------------------------------------

import time
from math import log
import ht16k33_driver                # Display's driver
from GPS_parser import GPS_handler   #
from button import Button            #
from imu import MPU6050              # Accelerometer
from mcp3208 import MCP3208          # Analog to digital converter
from dictionnary import Dictionnary  # Used for translations
from unit import Unit                # Handles metric to imperial conversions
from machine import UART, I2C, Pin, RTC, WDT, SPI, ADC, time_pulse_us, Timer
from timer import Timer_, LapTimer   #
import ujson as json                 #
from memory import access_setting    #
import fota_master                   # Handles Over The Air Firmware updates
from FOTA import connect_to_wifi, is_connected_to_wifi, server
from FOTA.ota import OTAUpdater      #
import os                            #
import logging                       #
from ds3231 import DS3231            # Real time clock
import gc                            # Garbage collector, used to free up unused memory
import injector_pulse_analyzer       #
from rp2 import StateMachine         # StateMachine allow for PIO support, used in fuel consumption
                                     # for precise timing of injector pulses
                
class OBC:
    def __init__(self):
        self.pwr_pin = Pin(0, Pin.OUT) # Used to latch power on/off
        self.pwr_pin.high()
        self.accy = Pin(28, Pin.IN)
        self.powered = True
        self.led = Pin("LED", Pin.OUT) #RPi's internal LED
        self.led.high()
        self.init_communication() # Initiates I2C and SPI communication to RTC, display, MPU and ADC
        
        if self.get_ignition_status():
            self.power_on_trigger = 'Ignition'
        else:
            self.power_on_trigger = 'SET_press'
            self.display.fill()
            self.display.show()
            while Pin(12, Pin.IN, Pin.PULL_DOWN).value(): #Prevents unwanted SET press when powering-on
                pass
                
        
        self.display.brightness(access_setting('display_brightness'))
        
        #self.buttonX = Button(pin_number, button_id, function)
        self.button1 = Button(4, 1, self.function_manager)
        self.button2 = Button(5, 2, self.function_manager)
        self.button3 = Button(6, 3, self.function_manager)
        self.button4 = Button(7, 4, self.function_manager)
        self.button5 = Button(8, 5, self.function_manager)
        self.button6 = Button(9, 6, self.function_manager)
        self.button7 = Button(10, 7, self.function_manager)
        self.button8 = Button(11, 8, self.function_manager)
        self.button9 = Button(12, 9, self.set_reset)    
        self.button10 = Button(13, 10, self.digit_manager)
        self.button11 = Button(14, 11, self.digit_manager)
        self.button12 = Button(15, 12, self.digit_manager)
        self.button13 = Button(20, 13, self.digit_manager)
        self.stalk_button = Button(21, 14, self.stalk_handler)
        
        self.digit_pressed = 0
       
        
        # Refresh_rate_adjuster is used to lower the refresh rate of certain displayed values,
        # by averaging temporary data
        self.refresh_rate_adjuster = {'timestamp':None,'values':[]} 
   
        # The OBC has a dedicated always running DS3231 RTC,
        # which is used to set the RPi's internal RTC
        self.rpi_rtc = RTC()
        try:
            self.rpi_rtc.datetime(self.rtc.datetime())
        except OSError:
            self.rtc = RTC()
        self.clock_format = access_setting("clock_format")

        self.timer = Timer_()
        self.laptimer = LapTimer()
        self.acceleration_timer = Timer_()
        self.speed_limit = 0
        self.speed_limit_is_active = False
        self.max_oil_temperature = 0
        self.oil_temperature_limit_is_active = False
        
        language = access_setting("language")
        self.words = Dictionnary(language).words
        unit = access_setting("unit")
        self.unit = Unit(unit)
        self.wiring = access_setting("wiring")
        
        self.cabin_light = Pin(22, Pin.IN, Pin.PULL_DOWN)
        self.cabin_light.irq(handler = self.cabin_light_handler, trigger = Pin.IRQ_RISING | Pin.IRQ_FALLING)
        
        if self.wiring == "OBC": #fuel related inits
            self.injector_pulse = Pin(27, Pin.IN)
            self.injector_cc = access_setting("inj_cc")
            self.cyl_nb = access_setting("cyl_nb")
            self.inj_cal = access_setting("inj_cal")
            self.sm0 = StateMachine(0, injector_pulse_analyzer.pulse_width, in_base=self.injector_pulse, jmp_pin=self.injector_pulse)
            self.sm1 = StateMachine(1, injector_pulse_analyzer.period, in_base=self.injector_pulse, jmp_pin=self.injector_pulse)
            self.new_sample = False
            self.sm0.irq(self.pulseIrqHandler)
            # The statemachine enters an infinite loop if the engine is stopped,
            # so we use an interrupt system to check if injector pulse is detected
            self.sm0.active(1)
            self.sm1.active(1)
    
            

        self.setting_index = 0 # Used in the setting menu, accessed by simultaneously pressing 1000 and 10.
        
        self.displayed_function = self.hour # self.displayed_function is what the infinite loop is contineously running
        self.last_displayed_function = None
        
        self.last_use = time.ticks_ms() # Used for auto-off
        self.can_switch_function = True
        
        # Used to periodically schedule tasks in order to optimize ressources
        self.priority_counter = 0 
        self.priority_interval = [1,20,40]
        self.watchdog = WDT(timeout=5000)
        
        logging.info('> System initialized!')
        
        self.loop()
    
# -------------------------SYSTEM RELATED FUNCTIONS----------------------------

    def init_communication(self):
        self.uart = UART(0, baudrate=115200 , rx=Pin(1), tx=None, stop = 1, parity = None, bits = 8 )
        self.gps = GPS_handler(self.uart)
        i2c = I2C(id=1, sda=Pin(2), scl=Pin(3), freq = 115200)
        self.rtc = DS3231(i2c)
        self.rtc = RTC()
        self.display = ht16k33_driver.Seg14x4(i2c)
        self.display.clear()
        self.display.show()
        self.mpu = MPU6050(i2c,device_addr = 1)
        spi = SPI(0, sck=Pin(18),mosi=Pin(19),miso=Pin(16), baudrate=50000)
        spi_cs = Pin(17, Pin.OUT)
        self.adc = MCP3208(spi, spi_cs)
    
    
    def power_handler(self,trigger = None):
        self.powered = not self.powered
        if self.powered:
            logging.debug("> System powered on")
            self.pwr_pin.high()
            self.init_communication()
            self.led.high()
        else:
            while self.cabin_light_handler() and not self.button9.pin.value() and not self.get_ignition_status():                
                self.display.put_text('LIGHTS') #TODO: DICTIONNARY FOR LIGHT
                self.display.show()
                self.display.blink_rate(1)
                time.sleep_ms(50)
            if not self.get_ignition_status() or trigger == "SET_press":
                logging.debug("> System powered off")
                self.uart.deinit()
                self.pwr_pin = Pin(0, Pin.OUT)
                self.display.clear()
                self.display.blink_rate(0)
                self.display.show()
                time.sleep_ms(50)
                self.pwr_pin.low()
                self.led.low()
            else:
                self.display.blink_rate(0)
                self.powered = True
            
            
    def check_for_last_use(self):
        auto_off_delay = access_setting('auto_off_delay')
        auto_off_delay = auto_off_delay * 60 * 60 * 1000
        if time.ticks_diff(time.ticks_ms(),self.last_use) > auto_off_delay:
            logging.debug(f"> No activity for {auto_off_delay}ms")
            self.power_handler()
            
    def cabin_light_handler(self, pin = None):
        display_brightness = access_setting('display_brightness')
        if self.cabin_light.value():
            if display_brightness > 5:
                self.display.brightness(display_brightness - 5)
            else:
                self.dispay.brightness(0)
            return True
        else:
            self.display.brightness(display_brightness)
            return False
    
    
    def get_ignition_status(self): #TODO: TROUBLESHOOTING: IRQ based ignition management will be done with upcoming PCB        
        return self.accy.value()

    
    
    def available_function_manager(self, functions_list): # Only enables functions availabe with the present car's wiring and sensors
        sensors = access_setting('sensors')
        if sensors != 'V+OIL':
            functions_list.remove(self.pressure)
            functions_list.remove(self.oil_temperature)
        if self.wiring == 'A.CLOCK':
            functions_list.remove(self.out_temperature)
        if self.wiring != 'OBC':
            fuel_related_functions = [self.fuel_range, self.remaining_fuel, self.inst_hourly_fuel_cons, self.inst_mpg]
            for function in fuel_related_functions:
                if function in functions_list:
                    functions_list.remove(function)
        return functions_list
        
    def stalk_handler(self, button_id, long_press):
        self.last_use = time.ticks_ms()
        self.digit_pressed = 0
        if not self.powered: # Wakes up the OBC if stalk is pressed
            self.power_handler()
            return 
        supported_functions = [self.hour, self.date, self.speed, self.acceleration, self.lap_timer, self.inst_hourly_fuel_cons,
                               self.inst_mpg, self.fuel_range, self.remaining_fuel, self.odometer, self.timer_function, self.pressure,
                               self.oil_temperature, self.out_temperature, self.voltage, self.altitude, self.heading, self.g_sensor]
        
        available_functions = self.available_function_manager(supported_functions)
        
        if self.displayed_function in supported_functions and self.can_switch_function:
            index = supported_functions.index(self.displayed_function)
            if not long_press:
                self.displayed_function = available_functions[(index+1) % len(available_functions)]
            else:
                if index == 0:
                    self.displayed_function = available_functions[len(available_functions) - 1]
                else:
                    self.displayed_function = available_functions[(index-1) % len(available_functions)]
            
        
    def function_manager(self, button_id, long_press):
        self.last_use = time.ticks_ms()
        self.digit_pressed = 0
        if not self.powered: # Wakes up the OBC if function is switched
            self.power_handler() 
        if self.can_switch_function: 
            if button_id == 1:
                if self.displayed_function == self.hour:
                    self.displayed_function = self.date
                else:
                    self.displayed_function = self.hour

            elif button_id == 2:
                self.displayed_function = self.speed


            elif button_id == 3:
                self.displayed_function = self.acceleration
                
                
            elif button_id == 4:
                self.displayed_function = self.lap_timer
                

            elif button_id == 5:
                if self.wiring == "OBC":
                    fuel_related_functions = [self.inst_hourly_fuel_cons, self.inst_mpg, self.fuel_range, self.remaining_fuel, self.odometer]
                    if not self.displayed_function in fuel_related_functions or self.displayed_function == self.odometer:
                        self.displayed_function = self.inst_hourly_fuel_cons
                    else:
                        index = fuel_related_functions.index(self.displayed_function)
                        if not long_press:
                            self.displayed_function = fuel_related_functions[index+1]
                        else:
                            if index == 1:
                                self.displayed_function = fuel_related_functions[len(fuel_related_functions)-1]
                            else:
                                self.displayed_function = fuel_related_functions[index-1]
                else:
                    self.displayed_function = self.odometer


            elif button_id == 6:
                if self.displayed_function == self.timer_function:
                    self.timer.is_displayed = True
                    if self.timer.lap_start != 0:
                        if self.timer.is_running:
                            self.timer.lap()
                        else:
                            self.timer.reset()
                else:
                    self.displayed_function = self.timer_function
                    self.timer.is_displayed = False
                    
                

            elif button_id == 7:
                # Depends of which sensors and wiring are equipped
                sensors = access_setting('sensors') #V / V+OIL
                supported_gauges = [self.pressure, self.oil_temperature, self.out_temperature,self.voltage]
                available_gauges = self.available_function_manager(supported_gauges)
                
                if not self.displayed_function in available_gauges or self.displayed_function == self.voltage:
                    self.displayed_function = available_gauges[0]
                else:
                    index = available_gauges.index(self.displayed_function)
                    if not long_press:
                        self.displayed_function = available_gauges[index+1]
                    else:
                        if index != 0:
                            self.displayed_function = available_gauges[index-1]
                        else:
                            self.displayed_function = available_gauges[len(available_gauges)-1]
                        
            
            elif button_id == 8:
                if self.displayed_function == self.g_sensor:
                    self.displayed_function = self.heading
                elif self.displayed_function == self.heading:
                    self.displayed_function = self.altitude
                else:
                    self.displayed_function = self.g_sensor
        else:
            logging.debug("> Switching function not allowed")
            
        logging.info(f"> Displayed function: {self.displayed_function.__name__}")


    def digit_manager(self, button_id, long_press):
        self.last_use = time.ticks_ms()
        if self.displayed_function in (self.set_hour, self.set_date, self.set_year, self.set_limit, self.set_odometer_thousands,
                                       self.set_odometer_hundreds, self.set_max_oil_temperature, self.set_setting, self.set_language,
                                       self.set_clock_format, self.set_unit,self.set_wiring,self.set_display_brightness,self.set_sensors,
                                       self.set_auto_off,self.set_gsensor_error, self.set_logging, self.set_injector_cc, self.set_cyl_nb,
                                       self.set_injector_calibration):
            if not long_press: 
                digit_map = {10: 1000, 11: 100, 12: 10, 13:1}
                self.digit_pressed = digit_map.get(button_id)
            else: # Long presses decrements the digit by their corresponding values
                digit_map = {10: -1000, 11: -100, 12: -10,13:-1}
                self.digit_pressed = digit_map.get(button_id)
        else:
            # Setting menu accessed by simultaneously pressing 1000 + 10 
            if (button_id == 10 and not self.button12.pin.value()) or (button_id == 12 and not self.button10.pin.value()):
                self.displayed_function = self.set_setting
                self.display.fill() #To check for potential dead pixels
                self.display.show()
                time.sleep_ms(2000)

    def set_reset(self, button_id, long_press):
        self.last_use = time.ticks_ms()
        self.digit_pressed = 0
        setting_functions = [self.set_language, self.set_clock_format, self.set_unit,
                     self.sw_update, self.set_display_brightness, self.set_sensors,
                     self.set_wiring, self.set_auto_off, self.set_gsensor_error,
                     self.set_logging, self.set_injector_cc, self.set_cyl_nb,
                     self.set_injector_calibration]

        if not long_press:
            if not self.powered:
                self.power_handler()
                
            elif self.displayed_function == self.hour:
                self.displayed_function = self.set_hour
                self.display.blink_rate(1)
                self.can_switch_function = False

            elif self.displayed_function == self.set_hour:
                self.displayed_function = self.hour
                self.display.blink_rate(0)
                self.can_switch_function = True

            elif self.displayed_function == self.date:
                self.displayed_function = self.set_year
                self.display.blink_rate(1)
                self.can_switch_function = False

            elif self.displayed_function == self.set_year:
                self.displayed_function = self.set_date

            elif self.displayed_function == self.set_date:
                self.displayed_function = self.date
                self.display.blink_rate(0)
                self.can_switch_function = True

            elif self.displayed_function == self.timer_function:
                if not self.timer.is_running:
                    self.timer.start()
                else:
                    self.timer.stop()

            elif self.displayed_function == self.lap_timer:
                if self.laptimer.is_running:
                    self.laptimer.end()
                elif self.gps.parsed.fix_type:
                    self.laptimer.reset_laptimer()
                    self.laptimer.start()
            
            elif self.displayed_function == self.acceleration:
                if self.acceleration_timer.start_time is not None:
                    self.acceleration_timer.reset()
                
            
            elif self.displayed_function == self.speed:
                self.displayed_function = self.set_limit
                self.can_switch_function = False
                self.display.blink_rate(1)
                
            
            elif self.displayed_function == self.set_limit:
                self.display.blink_rate(0)
                self.displayed_function = self.speed
                self.speed_limit_is_active = not self.speed_limit_is_active
                self.can_switch_function = True

            elif self.displayed_function == self.check_for_overspeed:
                self.speed_limit_is_active = False
                self.display.blink_rate(0)
                self.can_switch_function = True
                
                
            elif self.displayed_function == self.odometer:
                self.display.blink_rate(0)
                self.displayed_function = self.set_odometer_thousands
                self.can_switch_function = False

            elif self.displayed_function == self.set_odometer_thousands:
                self.display.blink_rate(0)
                self.displayed_function = self.set_odometer_hundreds
                
                
            elif self.displayed_function == self.set_odometer_hundreds:
                self.display.blink_rate(0)
                self.displayed_function = self.odometer
                self.can_switch_function = True
            
            elif self.displayed_function == self.oil_temperature:
                self.display.blink_rate(1)
                self.displayed_function = self.set_max_oil_temperature
                self.can_switch_function = False

            elif self.displayed_function == self.set_max_oil_temperature:
                self.display.blink_rate(0)
                self.displayed_function = self.oil_temperature
                self.oil_temperature_limit_is_active = not self.oil_temperature_limit_is_active
                self.can_switch_function = True
            
            elif self.displayed_function == self.check_for_overheat:
                self.display.blink_rate(0)
                self.oil_temperature_limit_is_active = False
                self.can_switch_function = True
            
            elif self.displayed_function == self.set_setting:
                try:
                    self.displayed_function = setting_functions[self.setting_index]
                except IndexError:
                    pass
               
            elif self.displayed_function == self.sw_update:
                fota_master.machine_reset()
                
            elif self.displayed_function in setting_functions:
                self.displayed_function = self.set_setting
            
            logging.info(f"> Displayed function: {self.displayed_function.__name__}")
       
        else: # Power-off if set is long pressed 
            if self.can_switch_function:
                self.power_handler(trigger = 'SET_press')
                
        
    def show(self, text):
        if self.powered:
            self.display.clear()
            self.display.put_text(text)
            self.display.show()

    def show_function_name(self, button): # Shows function's name when corresponding button is pressed
        now = time.ticks_ms()
        if time.ticks_diff(now, button.current_press['release']) < 700 or time.ticks_diff(now, self.stalk_button.current_press['release']) < 700:
            return True
        else:
            return False

# ---------------------------OBC FUNCTIONS-----------------------------

    def hour(self):
        if self.show_function_name(self.button1):
            self.show(self.words['HOUR'])
        else:
            current_time = self.rtc.datetime()
            self.show_hour(current_time)

    def set_hour(self):
        current_time = self.rtc.datetime()
        year, month, day, week_day, hour, minute, second, ms = current_time[0], current_time[1], current_time[2], \
            current_time[3], current_time[4], current_time[5], 0, current_time[7]
        digit_mapping = {
            1000: (10, 0),
            100: (1, 0),
            10: (0, 10),
            1: (0, 1),
            -1: (0, -1),
            -10: (0, -10),
            -100: (-1, 0),
            -1000: (-10, 0)
        }

        if self.digit_pressed in digit_mapping:
            hour_change, minute_change = digit_mapping[self.digit_pressed]
            hour += hour_change
            minute += minute_change
            hour = hour % 24
            minute = minute % 60
            current_time = (year, month, day, hour, minute, second, week_day)
            self.rtc.datetime(current_time)
            self.digit_pressed = 0
        self.show_hour(self.rtc.datetime())

    def show_hour(self, time_to_show):
        minute = "{:02d}".format(time_to_show[5])
        second = time_to_show[6]
        if self.clock_format == 24:
            hour = "{:02d}".format(time_to_show[4])
            if second % 2 == 0:  # Makes the dot blink
                self.show(' ' + hour + '.' + minute) 
            else:
                self.show(' ' + hour + minute)
        else:
            hour = time_to_show[4]
            hour_suffix = 'AM' if hour < 12 else 'PM'
            hour = "{:02d}".format(hour % 12)
            if hour == "00":
                hour = "12"
            if second % 2 == 0:
                self.show(hour + '.' + minute + hour_suffix)
            else:
                self.show(hour + minute + hour_suffix)
                

    def date(self):
        if self.show_function_name(self.button1):
            self.show(self.words['DATE'])
        else:
            current_time = self.rtc.datetime()
            self.show_date(current_time, display_year=False)

    def set_year(self):
        current_time = self.rtc.datetime()
        year, month, day, week_day, hour, minute, second, ms = current_time[0], current_time[1], current_time[2], \
            current_time[3], current_time[4], current_time[5], 0, current_time[7]
        digit_mapping = {
            10: 10,
            1: 1,
            -1: -1,
            -10: -10
        }

        if self.digit_pressed in digit_mapping:
            year += digit_mapping[self.digit_pressed]
            if year > 2100 or year < 1986: # I hope one OBC makes it to 2100!
                year = 2025
            current_time = (year, month, day, hour, minute, second, week_day)
            self.rtc.datetime(current_time)
            self.digit_pressed = 0
        self.show_date(current_time, display_year=True)

    def set_date(self):
        current_time = self.rtc.datetime()
        year, month, day, week_day, hour, minute, second, ms = current_time[0], current_time[1], current_time[2], \
            current_time[3], current_time[4], current_time[5], 0, current_time[7]
        digit_mapping = {
            1000: (10, 0),
            100: (1, 0),
            10: (0, 10),
            1: (0, 1),
            -1: (0, -1),
            -10: (0, -10),
            -100: (-1, 0),
            -1000: (-10, 0)
        }

        if self.digit_pressed in digit_mapping:
            day_change, month_change = digit_mapping[self.digit_pressed]
            day += day_change
            month += month_change
            if day > 31 or day < 1:
                day = 1
            if month > 12 or month < 1:
                month = 1
            current_time = (year, month, day, hour, minute, second, week_day)
            self.rtc.datetime(current_time)
            self.digit_pressed = 0
        self.show_date(current_time, display_year=False)

    def show_date(self, date_to_show, display_year=False):
        if display_year:
            self.show(str(date_to_show[0]))
        else:
            months = self.words['months']
            day = date_to_show[2] 
            month = date_to_show[1]
            month_str = months[month - 1]

            if day < 10:
                day_str = '0' + str(day)
            else:
                day_str = str(day)

            self.show(day_str + ' ' + month_str)
            
            
    def speed(self):
        if self.show_function_name(self.button2):
            self.show(self.words['SPEED'])
        elif self.show_function_name(self.button9):
            if self.speed_limit_is_active:
                self.show('  ON  ')
            else:
                self.show(' OFF  ')
        else:
            if self.gps.has_fix():
                speed = self.gps.parsed.speed[self.unit.speed_index]
                self.show(str(int(speed))+self.unit.speed_acronym)
            else:
                self.show(self.words['SIGNAL'])
                
                
    def set_limit(self):
        if self.show_function_name(self.button9):
            self.show(self.words['LIMIT'])
        else:
            digit_mapping = {
                100: (100),
                10: (10),
                1: (1),
                -1: (-1),
                -10: (-10),
                -100: (-100)
            }

            if self.digit_pressed in digit_mapping:
                delta = digit_mapping[self.digit_pressed]
                if self.digit_pressed in [-1, -10, -100] and self.speed_limit % 10 != 0:
                    self.speed_limit -= self.speed_limit % 100 % 10 #TODO: Check why this is even for?
                self.speed_limit += delta
                if self.speed_limit > 400 or self.speed_limit < 0: # Doubt an e30 ever made it to 300
                    self.speed_limit = 0
                self.digit_pressed = 0
            self.show(str(self.speed_limit) + self.unit.speed_acronym)


    def check_for_overspeed(self):
        if not self.displayed_function == self.set_limit and self.can_switch_function:
            if self.gps.has_fix():
                current_speed = self.gps.parsed.speed[self.unit.speed_index]
                gone_overspeed = False
                switching = True
                if current_speed > self.speed_limit and self.speed_limit_is_active:
                    logging.car("> Entering overspeed at {current_speed}")
                while current_speed > self.speed_limit and self.speed_limit_is_active and self.gps.has_fix():
                    self.watchdog.feed()
                    self.last_displayed_function = self.displayed_function
                    self.displayed_function = self.check_for_overspeed
                    gone_overspeed = True
                    self.can_switch_function = False
                    self.display.blink_rate(1) #TODO: Make it blink faster?
                    switching = not switching
                    if switching:
                        self.show(self.words['LIMIT'])
                    else:
                        self.show(str(int(current_speed)) + self.unit.speed_acronym)
                    start = time.ticks_ms()
                    while time.ticks_diff(time.ticks_ms(),start) < 1000:
                        pass
                    self.gps.get_GPS_data()
                    current_speed = self.gps.parsed.speed[self.unit.speed_index]
                if gone_overspeed:
                    self.display.blink_rate(0)
                    self.can_switch_function = True
                    self.displayed_function = self.last_displayed_function
    
    def acceleration(self):
        if self.show_function_name(self.button3):
            self.show(self.words['ACCEL'])
        else:
            if self.gps.has_fix():
                # if the acceleration timer is not running yet
                if not self.acceleration_timer.is_running and self.acceleration_timer.start_time == None and not self.acceleration_timer.show_lap_time():
                    acceleration = self.mpu.accel
                    self.display.blink_rate(0)
                    self.can_switch_function = True
                    if self.gps.parsed.speed[2] > 2:
                        self.show(self.words['STOP'])
                    else:
                        self.show(self.words['READY'])
                    
                    if acceleration.x > 0.5 and self.gps.parsed.speed[2] < 2:
                        self.acceleration_timer.start()
                else:
                    # Acceleration timer is running
                    speed_target = 100 #kmh
                    if self.gps.parsed.speed[2] >= speed_target and self.acceleration_timer.is_running:
                        self.acceleration_timer.display_end_time = time.ticks_add(time.ticks_ms(),4000)
                        self.display.blink_rate(5)
                        self.can_switch_function = False
                        time_to_100 = self.acceleration_timer.parse_time(self.acceleration_timer.get_elapsed_time())
                        logging.car(f"> {speed_target}kmh reached in {time_to_100}.")
                        self.acceleration_timer.reset()
                    if self.acceleration_timer.show_lap_time():
                        pass
                    else:
                        time_to_show = self.acceleration_timer.get_elapsed_time()
                        self.show(self.acceleration_timer.parse_time(time_to_show))
                    
            else:
                self.show(self.words['SIGNAL'])


    def lap_timer(self):
        if self.show_function_name(self.button4):
            self.show(self.words['LAP'])
        else:  
            if self.gps.has_fix():
                if self.laptimer.is_running:
                    if self.laptimer.start_position is None:
                        self.laptimer.set_start_position(self.gps.parsed)
                    # Program goes faster than GPS updates, so we dismiss repetitive coordinates
                    if self.gps.parsed.longitude != self.gps.previous_place['longitude'] and self.gps.parsed.latitude != self.gps.previous_place['latitude']:
                        self.laptimer.check_for_completed_lap(self.gps.parsed) 
                    
                    # At the end of a lap, we display the time, the delay with the fastest lap (if any), and the number of laps. 
                    if self.laptimer.show_lap_time():
                        self.display.blink_rate(5)
                        self.can_switch_function = False
                        timer_str = self.laptimer.parse_time(self.laptimer.lap_time)
                        
                    elif self.laptimer.show_delay():
                        self.display.blink_rate(5)
                        self.can_switch_function = False
                        if self.laptimer.delay > 0:
                            timer_str = str(self.laptimer.parse_time(self.laptimer.delay, '+'))
                        else:
                            timer_str = str(self.laptimer.parse_time(self.laptimer.delay, '-'))
                        
                    elif self.laptimer.show_laps():
                        self.display.blink_rate(5)
                        self.can_switch_function = False
                        if self.laptimer.number_of_lap < 10:
                            timer_str = str(self.laptimer.number_of_lap - 1)+'  LAP'
                        else:
                            timer_str = str(self.laptimer.number_of_lap - 1)+' LAP'
                    else:
                        self.can_switch_function = True
                        self.display.blink_rate(0)
                        time_to_show = self.laptimer.get_elapsed_lap_time()
                        timer_str = self.laptimer.parse_time(time_to_show)
                    self.show(str(timer_str))
                else: # If lap timer is not running 
                    if self.laptimer.show_laps():
                        self.display.blink_rate(5)
                        self.can_switch_function = False
                        timer_str = "{:>6}".format(str(self.laptimer.number_of_lap))
                        
                    elif self.laptimer.show_lap_time():
                        self.display.blink_rate(5)
                        self.can_switch_function = False
                        timer_str = self.laptimer.parse_time(self.laptimer.fastest_lap[0])
                    else:
                        self.display.blink_rate(0)
                        self.can_switch_function = True
                        timer_str = self.words['READY']  
                    self.show(str(timer_str))
            else:
                self.show(self.words['SIGNAL'])
                
    def pulseIrqHandler(self,sm):
        if not self.new_sample:
            self.new_sample = True

    def get_hourly_fuel_cons(self):
            def scale(v):
                return (1 + (v ^ 0xffffffff)) * 24e-6  # Scale to ms

            time.sleep_ms(150) #timeout waiting for a new sample. Corresponds to 400rpm
            if self.new_sample:
                pulse_width = scale(self.sm0.get())
                period = scale(self.sm1.get())
                rpm = (1/(period/1000))* 60 
                self.new_sample = False
                print(f"rpm {rpm:.2f} period {period:.2f} pw {pulse_width:.2f}")

                injector_cc_per_ms = self.injector_cc / 60_000 
                fuel_per_pulse_cc = pulse_width * injector_cc_per_ms
                total_fuel_per_rot_cc = fuel_per_pulse_cc * self.cyl_nb / 2
                rotations_per_second = 1 / (period / 1_000)
                fuel_per_second_cc = (self.inj_cal / 100) * total_fuel_per_rot_cc * rotations_per_second
                fuel_per_hour_liters = (fuel_per_second_cc * 3600) / 1000 
            else:
                fuel_per_hour_liters = 0
            return fuel_per_hour_liters
                
    def inst_hourly_fuel_cons(self):
        def scale(v):
            return (1 + (v ^ 0xffffffff)) * 24e-6  # Scale to ms
        
        if self.show_function_name(self.button5):
            self.show(' L/H ') #TODO: Words for fuel
        else:
            fuel_per_hour_liters = self.get_hourly_fuel_cons()
            self.show("{:<3.1f}L/H".format(fuel_per_hour_liters))
                

    def inst_mpg(self):
        if self.show_function_name(self.button5):
            self.show('L/100 ') #TODO: Words for fuel
        else:
            fuel_per_hour_liters = self.get_hourly_fuel_cons()
            speed_kmh = self.gps.parsed.speed[self.unit.speed_index]
            if speed_kmh > 0:
                fuel_per_100km = (fuel_per_hour_liters / speed_kmh) * 100
            else:
                fuel_per_100km = 0  
            self.show("{:<3.1f}L/1.".format(fuel_per_100km))
            
            
    def fuel_range(self):
        if self.show_function_name(self.button5):
            self.show('RANGE') #TODO: Words for fuel
        else:
            self.show('9999KM')

    def remaining_fuel(self):
        if self.show_function_name(self.button5):
            self.show('FUEL')
        else:
            if time.ticks_diff(time.ticks_ms(), self.refresh_rate_adjuster['timestamp']) > 500:
                self.refresh_rate_adjuster['timestamp'] = time.ticks_ms()
                voltage = self.adc.read_voltage(4)
                self.show(round(voltage,1))
                #fuel = 55*voltage
                #fuel_str = '{:<5}L'.format(round(fuel,0))
                #self.show(fuel_str) 


    def odometer(self):
        if self.show_function_name(self.button5):
            self.show(self.words['ODO'])
        else:
            value = access_setting('odometer')
            value = round(value,1)
            if value%1!=0:
                value_str = "{:>7}".format(value)
            elif value < 100000: # Wonder if there is  any >1Mkm miled e30s out there but hey
                value_str = "{:>6}".format(value)
            self.show(str(value_str))
    
            
    def set_odometer(self, unit):
        odometer_value = int(access_setting('odometer'))
        if unit == 'k':
            digit_mapping = {100: 100000, 10: 10000, 1: 1000, -1: -1000, -10: -10000, -100: -100000}
        else:
            digit_mapping = {1000: 1000, 100: 100, 10: 10, 1: 1, -1: -1, -10: -10, -100: -100, -1000: -1000}
        if self.digit_pressed in digit_mapping:
            odometer_value += digit_mapping.get(self.digit_pressed, 0)
            if odometer_value < 0:
                odometer_value = 0
            elif odometer_value > 999999:
                odometer_value = 0
            access_setting("odometer", odometer_value)
            self.digit_pressed = 0      
            
    def set_odometer_thousands(self):
        odometer_value = int(access_setting('odometer'))
        odometer_str = str(odometer_value)
        odometer_str = self.display.zeros_before_number(odometer_str)
        now = time.ticks_ms()
        time_to_adjuster = time.ticks_diff(self.refresh_rate_adjuster['timestamp'],now)
        if time_to_adjuster < 300:
            odometer_str = odometer_str[-3:]
            odometer_str = "{:>6}".format(odometer_str)
            if time_to_adjuster < 50:
                self.refresh_rate_adjuster['timestamp'] = time.ticks_add(now, 600)        
        
        self.show(odometer_str)
        self.set_odometer('k')
                
    def set_odometer_hundreds(self):
        odometer_value = int(access_setting('odometer'))
        odometer_str = str(odometer_value)
        odometer_str = self.display.zeros_before_number(odometer_str)
        now = time.ticks_ms()
        time_to_adjuster = time.ticks_diff(self.refresh_rate_adjuster['timestamp'],now)
        if time_to_adjuster < 300:
            odometer_str = odometer_str[:-3]
            
            if time_to_adjuster<50:
                self.refresh_rate_adjuster['timestamp'] = time.ticks_add(now, 600)
        self.show(odometer_str)
        self.set_odometer('h')
        
        
    def timer_function(self):
        if self.show_function_name(self.button6) and not self.timer.is_displayed:
            self.show(self.words['TIMER'])
        else:
            if not self.timer.show_lap_time():
                self.can_switch_function = True
                self.display.blink_rate(0)
                time_to_show = self.timer.get_elapsed_time()
            else:
                self.can_switch_function = False
                self.display.blink_rate(5)
                time_to_show = self.timer.lap_time
            
            timer_str = self.timer.parse_time(time_to_show)
            self.show(timer_str)
    
    def get_pressure(self):
        read_voltage = self.adc.read_voltage(1)
        bar_pressure = 2.59 * read_voltage - 1.29
        if bar_pressure < 0.2:
            bar_pressure = 0
        psi_pressure = round(bar_pressure * 14.5038,1)
        if self.unit.system == 'METRIC':
            return round(bar_pressure,1)
        elif self.unit.system == 'IMPERI.':
            return psi_pressure
        
        
    def pressure(self):
        if self.show_function_name(self.button7):
            self.show(self.words['OIL'])
        else:
            if time.ticks_diff(time.ticks_ms(), self.refresh_rate_adjuster['timestamp']) > 300:
                pressure = self.get_pressure()
                self.show(str(pressure) + ' ' + self.unit.pressure_acronym)
                self.refresh_rate_adjuster['timestamp'] = time.ticks_ms()
            
    def temperature_formatter(self, temperature):
        if temperature < -50:
            return 'NODATA'
        temperature_str = f"{temperature: 4.0f}{self.unit.temperature_acronym}"
        return temperature_str if temperature < 100 else ' ' + temperature_str
        
        
    def get_temperature(self, string, sensor):
        if sensor == "oil":
            voltage = self.adc.read_voltage(0)
            try:
                RNTC = (5000/voltage) - 1000
            except ZeroDivisionError: #TODO: No sensor detection
                RNTC = 10000            
            A = 1.291780e-3
            B = 2.612878e-4
            C = 1.568296e-7
        elif sensor == "out":
            voltage = self.adc.read_voltage(3)
            try:
                RNTC = (voltage * 4.7) / (5 - voltage)
                RNTC = 1000 * RNTC
            except ZeroDivisionError: #TODO: No sensor detection
                RNTC = 10000
            A = 1.327871e-3
            B = 2.297980e-4
            C = 1.375199e-7
        try:
            temperature = 1 /( A + B * log(RNTC) + C *(log(RNTC))**3)
        except:
            logging.exception(f"> Error while computing temperature. RNTC value: {RNTC}")
            temperature = 222
        celsius_temperature = temperature - 273.15
        fahrenheit_temperature = (celsius_temperature *  1.8) + 32
        if self.unit.system == 'METRIC':
            temperature_to_show = celsius_temperature
        elif self.unit.system == 'IMPERI.':
            temperature_to_show = fahrenheit_temperature
        if not string:
            return temperature_to_show            
        else:
            return self.temperature_formatter(temperature_to_show)
    
    
    def oil_temperature(self):
        if self.show_function_name(self.button7):
            self.show(self.words['TEMP'])
        elif self.show_function_name(self.button9):
            if self.oil_temperature_limit_is_active:
                self.show('  ON  ')
            else:
                self.show(' OFF  ')
        else:
            try:
                self.refresh_rate_adjuster['values'].append(self.get_temperature(False, "oil"))
            except MemoryError:
                logging.exception(f"> MemoryError in self.refresh_rate_updater. Array lenght: {len(self.refresh_rate_adjuster['values'])}") 
            
            if time.ticks_diff(time.ticks_ms(), self.refresh_rate_adjuster['timestamp']) > 1000:
                if len(self.refresh_rate_adjuster['values']) > 2:
                    rounded_temperature = sum(self.refresh_rate_adjuster['values']) / len(self.refresh_rate_adjuster['values'])
                    self.show(self.temperature_formatter(rounded_temperature))
                    self.refresh_rate_adjuster['values'].clear()
                else:
                    self.show(self.get_temperature(True, "oil"))
                self.refresh_rate_adjuster['timestamp'] = time.ticks_ms()
            
                    
    
    def set_max_oil_temperature(self):
        if self.show_function_name(self.button9):
            self.show(' MAX.')
        else:
            digit_mapping = {100: 100, 10: 10, 1: 1, -1: -1, -10: -10, -100: -100, -1000: -1000}
            if self.digit_pressed in digit_mapping:
                self.max_oil_temperature += digit_mapping[self.digit_pressed]
                if self.max_oil_temperature > 150 or self.max_oil_temperature < 0:
                    self.max_oil_temperature = 0
                self.digit_pressed = 0
            max_oil_temperature_str = self.temperature_formatter(self.max_oil_temperature)
            self.show(max_oil_temperature_str)
    
    def check_for_overheat(self):
        if not self.displayed_function == set_max_oil_temperature and self.can_switch_function:
            oil_temperature = int(self.get_temperature(False, "oil"))
            switching = True
            gone_overheat = False
            if oil_temperature > self.max_oil_temperature and self.oil_temperature_limit_is_active:
                logging.car(f"> Oil overheating! Temperature: {oil_temperature}")
            while oil_temperature > self.max_oil_temperature and self.oil_temperature_limit_is_active:
                self.watchdog.feed()
                self.displayed_function = self.check_for_overheat
                self.can_switch_function = False
                gone_overheat = True
                self.display.blink_rate(1)
                if switching: 
                    self.show(self.words['TEMP'])
                else:
                    if time.ticks_diff(time.ticks_ms(), self.refresh_rate_adjuster['timestamp']) > 1000:
                        self.show(self.get_temperature(True, "oil"))
                        self.refresh_rate_adjuster['timestamp'] = time.ticks_ms()
                switching = not switching
                start = time.ticks_ms()
                while time.ticks_diff(time.ticks_ms(), start) < 1000:
                    pass
                temperature = int(self.get_temperature(False, "oil"))
            if gone_overheat:
                logging.car("> Stopped overheating.")
                self.display.blink_rate(0)
                self.can_switch_function = True
                self.displayed_function = self.oil_temperature
        
    
    def out_temperature(self): #TODO: <3 degrees alert
        if self.show_function_name(self.button7):
            self.show('OUTEMP') #TODO: Words for outside temp
        else:
            try:
                self.refresh_rate_adjuster['values'].append(self.get_temperature(False, "out"))
            except MemoryError:
                logging.exception(f"> MemoryError in self.refresh_rate_updater. Array lenght: {len(self.refresh_rate_adjuster['value'])}")
            if time.ticks_diff(time.ticks_ms(), self.refresh_rate_adjuster['timestamp']) > 1000:
                if len(self.refresh_rate_adjuster['values']) > 2:
                    rounded_temperature = sum(self.refresh_rate_adjuster['values']) / len(self.refresh_rate_adjuster['values'])
                    self.show(self.temperature_formatter(rounded_temperature))
                    self.refresh_rate_adjuster['values'].clear()
                else:
                    self.show(self.get_temperature(True, "out"))
                self.refresh_rate_adjuster['timestamp'] = time.ticks_ms()
        
    def get_voltage(self):
        adc_voltage = self.adc.read_voltage(2)
        battery_voltage = adc_voltage * 3
        return battery_voltage
    
    def voltage(self):
        if self.show_function_name(self.button7):
            self.show(self.words['VOLT'])
        else:
            if time.ticks_diff(time.ticks_ms(), self.refresh_rate_adjuster['timestamp']) > 1000:
                self.refresh_rate_adjuster['timestamp'] = time.ticks_ms()
                battery_voltage_str = "{:.1f}".format(self.get_voltage())
                self.show(' ' + battery_voltage_str + 'V')

    def altitude(self):
        if self.show_function_name(self.button8):
            self.show(self.words['ALT'])
        else:
            if self.gps.has_fix():
                if self.unit.system == 'METRIC':
                    altitude = self.gps.parsed.altitude
                elif self.unit.system == 'IMPERI.':
                    altitude = self.gps.parsed.altitude * 3.28084
                self.show(str(int(altitude)) + self.unit.altitude_acronym)
            else:
                self.show(self.words['SIGNAL'])

    def heading(self):
        if self.show_function_name(self.button8):
            self.show(self.words['HDG'])
        else:
            if self.gps.has_fix():
                compass_direction = self.gps.parsed.compass_direction()
                heading = self.gps.parsed.course
                self.show(str(int(heading)) + compass_direction)
            else:
                self.show(self.words['SIGNAL'])

    def g_sensor(self):
        if self.show_function_name(self.button8):
            self.show(self.words['G SENS'])
        else:
            if time.ticks_diff(time.ticks_ms(), self.refresh_rate_adjuster['timestamp']) > 200:
                g_error = access_setting('g_error')
                self.refresh_rate_adjuster['timestamp'] = time.ticks_ms()
                acceleration = self.mpu.accel
                g_vector = ((acceleration.x + (g_error[0]/10)) ** 2 + (acceleration.z + (g_error[1]/10)) **2) ** 0.5
                self.show(' ' + str(round(g_vector, 1)) + 'G')
                
# ----------------------------SETTINGS FUNCTIONS-------------------------------

    def set_setting(self):
        digit_mapping = {10,1,-1,-10}
        if self.digit_pressed in digit_mapping:
            self.setting_index+=self.digit_pressed
            if self.setting_index>12 or self.setting_index < 0:
                self.setting_index = 0
            self.digit_pressed = 0
        self.show('SET{:>3}'.format(str(self.setting_index)))
    
    def set_language(self):
        if self.show_function_name(self.button9):
            self.show('LANGUA.')
        else:
            language = access_setting('language')
            possible_languages = ['EN','FR','DE']
            index = possible_languages.index(language)
            digit_mapping = {1:1, -1:-1}
            if self.digit_pressed in digit_mapping:
                index+= digit_mapping[self.digit_pressed]
                if index >= len(possible_languages) or index < 0:
                    index = 0
                access_setting('language',possible_languages[index])
                self.words = Dictionnary(possible_languages[index]).words
                self.unit.update()
                self.digit_pressed = 0
            self.show(access_setting('language'))
    
    def set_clock_format(self):
        if self.show_function_name(self.button9):
            self.show('12/24')
        else:
            if self.clock_format == 24:
                self.show('24H')
            else:
                self.show('12AMPM')
            if self.digit_pressed in [-1,1]:
                self.clock_format = 12 if self.clock_format == 24 else 24
                access_setting('clock_format',clock_format)
                self.digit_pressed = 0
            
    def set_unit(self):
        if self.show_function_name(self.button9):
            self.show('UNIT')
        else:
            unit = access_setting('unit')
            possible_units = ['METRIC','IMPERI.']
            index = possible_units.index(unit)
            digit_mapping = [1, -1]
            if self.digit_pressed in digit_mapping:
                index+=self.digit_pressed
                if index >= 2 or index < 0:
                    index = 0
                access_setting('unit', possible_units[index])
                self.unit.system = possible_units[index]
                self.unit.update()
                self.digit_pressed = 0
            self.show(access_setting('unit'))
    
    def sw_update(self):
        if self.show_function_name(self.button9):
            self.show('UPDATE')
        else:
            self.show(' WIFI ')
            self.can_switch_function = False
            try:
                os.stat("wifi.json")
                with open("wifi.json", 'r') as f:
                    wifi_current_attempt = 1
                    wifi_credentials = json.load(f)
                    
                while (wifi_current_attempt < 3):
                    try:
                        ip_address = connect_to_wifi(wifi_credentials["ssid"], wifi_credentials["password"])
                    except:
                        logging.exception('> Exception occured while connecting to wifi.')
                    if is_connected_to_wifi():
                        logging.debug(f"> Connected to wifi, IP address {ip_address}")
                        self.show('CNNCTD')
                        time.sleep(2)
                        self.show(wifi_credentials["ssid"][:6])
                        time.sleep(2)
                        break
                    else:
                        wifi_current_attempt += 1
            
            except OSError:
                logging.debug("> OSError occured as wifi.json doesn't exist")
                with open('wifi.json', 'w') as f:
                    json.dump({}, f)
                
            if is_connected_to_wifi():
                logging.debug("> Entering update mode.")
                firmware_url = "https://github.com/80sEngineering/E30-OBC/"
                files_to_update = ["button.py", "dictionnary.py", "ds3231.py", "fota_master.py",
                                   "GPS_parser.py","ht16k33_driver.py","imu.py","logging.py",
                                   "main.py", "mcp3208.py", "memory.py", "timer.py", "unit.py",
                                   "vector3d.py","version.json"]
                ota_updater = OTAUpdater(firmware_url, files_to_update)
                ota_updater.check_for_updates()
                if ota_updater.newer_version_available:
                    self.show('NEW'+'{:>3}'.format('V'+str(ota_updater.latest_version)))
                    time.sleep(2)
                    self.show('UPDATE')
                    time.sleep(2)
                    ota_updater.download_update_and_reset()
                    
                else:
                    logging.debug("> No new updates available.")
                    self.show('LATEST')
                    time.sleep(2)
                    self.show('VERS.'+'{:>2}'.format(str(ota_updater.current_version)))
                    time.sleep(2)
                    self.display.clear()
                    self.display.show()
                    fota_master.machine_reset()
                    
            else:
                logging.debug(f"> Something went wrong, going into setup mode.")
                fota_master.setup_mode()
            
            server.run()

            
    def set_display_brightness(self):
        if self.show_function_name(self.button9):
            self.show('BRIGHT')
        else:
            brightness = self.display.brightness()
            self.show("{:>6}".format(brightness))
            if self.digit_pressed in [1,-1]:
                brightness+=self.digit_pressed
                if brightness >= 16 or brightness < 0:
                    brightness = 0
                self.display.brightness(brightness)
                access_setting('display_brightness',brightness)
                self.digit_pressed = 0
                
    
    def set_sensors(self):
        if self.show_function_name(self.button9):
            self.show('SENSOR')
        else:
            sensors = access_setting('sensors')
            self.show(sensors)
            if self.digit_pressed in [1,-1]:
                if sensors == 'V+OIL':
                    access_setting('sensors','V')
                else:
                    access_setting('sensors','V+OIL')
                self.digit_pressed = 0
            
                
    def set_wiring(self):
        if self.show_function_name(self.button9):
            self.show('WIRING')
        else:
            wiring = access_setting('wiring')
            wiring_list = ['A.CLOCK','D.CLOCK','OBC']
            self.show(str(wiring))
            if self.digit_pressed in [1,-1]:
                index = wiring_list.index(str(wiring))
                index = (index + self.digit_pressed) % 3
                wiring = wiring_list[index]
                access_setting('wiring', wiring) #TODO: Add safety in case A.CLOCK changes wiring.
                self.digit_pressed = 0
            
            
    def set_auto_off(self):
        if self.show_function_name(self.button9):
            self.show('AUT.OFF')
        else:
            auto_off_delay = access_setting('auto_off_delay')
            self.show(str(auto_off_delay)+'H')
            digit_mapping = {10:10,1:1, -1:-1,-10:-10}
            if self.digit_pressed in digit_mapping:
                auto_off_delay += self.digit_pressed
                self.digit_pressed = 0
                if auto_off_delay < 1 or auto_off_delay > 24:
                    auto_off_delay = 1
                access_setting('auto_off_delay',auto_off_delay)
                            
                
                
    def set_gsensor_error(self):
        if self.show_function_name(self.button9):
            self.show('G.ERROR')
        else:
            g_error = access_setting('g_error')
            self.show('X'+str(g_error[0])+'Y'+str(g_error[1]))
            x_digit_mapping = [10, -10]
            y_digit_mapping = [1, -1]
            if self.digit_pressed in x_digit_mapping:
                if -10 <= g_error[0] + self.digit_pressed / 10 < 10:
                     g_error[0] += int(self.digit_pressed / 100)
                access_setting('g_error',g_error)
            elif self.digit_pressed in y_digit_mapping:
                if -10 < g_error[1] + self.digit_pressed < 10:
                    g_error[1] += int(self.digit_pressed/10)
                access_setting('g_error',g_error)
            self.digit_pressed = 0
    
    def set_logging(self):
        if self.show_function_name(self.button9):
            self.show('LOG')
        else:
            all_logging_types = [0b111111,0b111110,0]
            current_logging_types = logging._logging_types
            if current_logging_types == 0b111111:
                self.show('DEBUG')
            elif current_logging_types == 0b111110:
                self.show('NORMAL')
            elif current_logging_types == 0:
                self.show('NONE')
        digit_mapping = {1,-1}
        if self.digit_pressed in digit_mapping:
            index = all_logging_types.index(current_logging_types)
            index = (index + self.digit_pressed) % 3
            logging._logging_types = all_logging_types[index]
            self.digit_pressed = 0
            
    def set_injector_cc(self):
        if self.show_function_name(self.button9):
            self.show('INJ. CC')
        else:
            injector_cc = access_setting("inj_cc")
            self.show(f"{injector_cc} CC")
            digit_mapping = {100,10,1,-1,-10,-100}
            if self.digit_pressed in digit_mapping:
                injector_cc += self.digit_pressed
                if injector_cc < 100:
                    injector_cc = 800
                elif injector_cc > 800:
                    injector_cc = 100
                access_setting("inj_cc",injector_cc)
                self.injector_cc = injector_cc
                self.digit_pressed = 0                
            
    
    def set_cyl_nb(self):
        if self.show_function_name(self.button9):
            self.show('CYL. NB')
        else:
            cyl_nb = access_setting("cyl_nb")
            self.show("{:<3}CYL".format(cyl_nb))
            if self.digit_pressed in {-1,1}:
                possible_cyl_nb = [4, 6, 8, 10, 12,'WTF']
                index = (possible_cyl_nb.index(cyl_nb) + self.digit_pressed) % len(possible_cyl_nb)
                cyl_nb = possible_cyl_nb[index]
                if cyl_nb == 'WTF':
                    self.show(' WTF  ')
                    cyl_nb = 4
                    time.sleep(1)
                access_setting("cyl_nb", cyl_nb)
                self.cyl_nb = cyl_nb
                self.digit_pressed = 0
                
                    
    def set_injector_calibration(self):        
        if self.show_function_name(self.button9):
            self.show('INJ.CAL.')
        else:
            calibration_factor = access_setting('inj_cal')
            self.show("{:>6}".format(calibration_factor))
            if self.digit_pressed in {-100,-10,-1,1,10,100}:
                calibration_factor += self.digit_pressed
                if calibration_factor > 999:
                    calibration_factor = 1
                elif calibration_factor < 1:
                    calibration_factor = 1
                access_setting('inj_cal', calibration_factor)
                self.inj_cal = calibration_factor
                self.digit_pressed = 0

                   
# -------------------------------INFINITE-LOOP---------------------------------

    def loop(self):
        while True:
            self.watchdog.feed()
            if self.powered:
                self.displayed_function()
                if self.priority_counter == self.priority_interval[1] or  self.priority_counter == self.priority_interval[2]: #1/20 occurence
                    #self.gps.get_GPS_data() #computing travelled distance
                    self.led.toggle()
                if self.priority_counter == self.priority_interval[2]: #1/40 occurence
                    gc.collect() # freeing memory space
                    self.check_for_last_use()
                    if self.wiring in ['D.CLOCK','OBC'] and self.power_on_trigger == 'Ignition':
                        if not self.get_ignition_status():
                            self.power_handler()
                    if self.speed_limit_is_active:
                        self.check_for_overspeed()
                    if self.oil_temperature_limit_is_active: 
                        self.c