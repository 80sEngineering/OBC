import time
import math
import logging

class Timer_:
    def __init__(self):
        self.start_time = None
        self.lap_start = None
        self.lap_time = 0
        self.elapsed_time = 0
        self.is_running = False
        self.is_displayed = False
        self.display_end_time = 0

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.start_time = time.ticks_ms()

    def stop(self):
        if self.is_running:
            self.is_running = False
            elapsed = time.ticks_diff(time.ticks_ms(), self.start_time)
            self.elapsed_time += elapsed
            self.start_time = None
            

    def reset(self):
        self.stop()
        self.lap_time = 0
        self.elapsed_time = 0
        self.lap_start = None
        
    def lap(self):
        logging.info(f"> Lap")
        now = time.ticks_ms()
        if self.lap_start is None:
            self.lap_start = now
        else:
            self.lap_time = time.ticks_diff(now, self.lap_start)
            self.lap_start = now
            self.display_end_time = time.ticks_add(now, 3000) 

    def get_elapsed_time(self):
        if self.is_running:
            return time.ticks_diff(time.ticks_ms(), self.start_time) + self.elapsed_time
        else:
            return self.elapsed_time

    def show_lap_time(self):
        now = time.ticks_ms()
        if self.display_end_time > now:
            return True
        else:
            return False

    def parse_time(self,time_to_show, sign = " "):
        hours = int(time_to_show / 3600000) % 10
        minutes = int(time_to_show / 60000) % 60
        seconds = int(time_to_show / 1000) % 60
        tenths = int(time_to_show / 100) % 10
        if hours:
            timer_str = "{:d}.{:02d}.{:02d}.{:01d}".format(hours, minutes, seconds, tenths)
        
        elif minutes > 9:
            timer_str =  sign + "{:02d}.{:02d}.{:01d}".format(minutes, seconds, tenths)
        elif minutes:
            timer_str = " " + sign + "{:01d}.{:02d}.{:01d}".format(minutes, seconds, tenths)
        
        elif seconds > 9:
            timer_str = "  " + sign + "{:02d}.{:01d}".format(seconds, tenths)
            
        else:
            timer_str = "   " + sign + "{:01d}.{:01d}".format(seconds, tenths)

        return timer_str
            
    
class LapTimer(Timer_):
    def __init__(self):
        Timer_.__init__(self)
        self.start_position = None
        self.previous_update = {'distance':0,'timestamp':None}
        self.number_of_lap = 1
        self.display_delay = 0
        self.display_laps = 0
        self.fastest_lap = None
        self.delay = 0
            
    def set_start_position(self,gps_data):
        self.start_position = {'latitude':gps_data.latitude[0],'longitude':gps_data.longitude[0],'course':gps_data.course,'timestamp':gps_data.timestamp}
        logging.car(f"> Starting position: {self.start_position}")
        
    def convert_to_local_coordinates(self, latitude, longitude):
        delta_latitude = latitude - self.start_position['latitude']
        delta_longitude = longitude -  self.start_position['longitude']
      
        latitude_to_meters = 111320  
        longitude_to_meters = 111320 * math.cos(math.radians(self.start_position['latitude']))
        
        x = delta_longitude * longitude_to_meters
        y = delta_latitude * latitude_to_meters
    
        return [x,y]
    
    
    def show_delay(self):
        now = time.ticks_ms()
        if self.display_delay > now:
            return True
        else:
            return False
        
        
    def show_laps(self):
        now = time.ticks_ms()
        if self.display_laps > now:
            return True
        else:
            return False
        
        
    def has_completed_lap(self):
        finish_time = self.previous_update['timestamp']
        logging.car(f"> Lap completed at {finish_time}.")
        if self.number_of_lap == 1:
            self.lap_time = time.ticks_diff(finish_time, self.start_time)
            self.fastest_lap = [self.lap_time,1]
        else:
            self.lap_time = time.ticks_diff(finish_time, self.lap_start)
            self.display_delay = time.ticks_add(finish_time,6000)
            self.delay = time.ticks_diff(self.lap_time,self.fastest_lap[0]) 
            if self.lap_time < self.fastest_lap[0]:
                self.fastest_lap = [self.lap_time,self.number_of_lap]
        self.lap_start = finish_time
        self.number_of_lap += 1
        self.display_end_time = time.ticks_add(finish_time, 3000)
    
    def get_elapsed_lap_time(self):
        if self.is_running and self.number_of_lap > 1:
            return time.ticks_diff(time.ticks_ms(), self.lap_start)
        elif self.is_running:
            return time.ticks_diff(time.ticks_ms(), self.start_time) + self.elapsed_time
        else:
            return self.elapsed_time        
        
    def check_for_completed_lap(self,gps_data):
        def get_heading_delta():
            delta = gps_data.course - self.start_position['course']
            abs_delta = abs(delta)

            if abs_delta == 180:
                return abs_delta
            elif abs_delta < 180:
                return delta
            elif gps_data.course > self.start_position['course']:
                return abs_delta - 360
            else:
                return 360 - abs_delta
            
        current_coords = self.convert_to_local_coordinates(gps_data.latitude[0], gps_data.longitude[0])
        distance = (current_coords[0]**2+current_coords[1]**2)**0.5
        can_check = False
        if self.number_of_lap == 1 and time.ticks_diff(time.ticks_ms(),self.start_time)>10000:
            can_check = True
        elif self.number_of_lap > 1 and time.ticks_diff(time.ticks_ms(),self.lap_start)>10000:
            can_check = True
        if can_check and distance < 10:
            distance_delta = distance - self.previous_update['distance']
            if (distance_delta > 0) and self.previous_update['distance'] != 0 and get_heading_delta() <= 30:
                self.previous_update['distance'] = 0
                self.has_completed_lap()
            else:
                self.previous_update['distance'] = distance
                self.previous_update['timestamp'] = time.ticks_ms()
            
            
    def end(self):
        logging.info("> Timer ended")
        now = time.ticks_ms()
        self.is_running = False
        if self.number_of_lap > 1:
            self.display_laps = time.ticks_add(now, 4000)
            self.display_end_time = time.ticks_add(now, 8000)
    
    def reset_laptimer(self):
        logging.info("> Timer reset")
        self.reset()
        self.start_time = None
        self.start_position = None
        self.previous_update['distance'] = 0
        self.number_of_lap = 1
        self.display_delay = 0
        self.display_laps = 0
        self.fastest_lap = None
        self.delay = 0
        
                
            
            
            
        
            
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
     
     
     