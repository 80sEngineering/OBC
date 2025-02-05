from memory import access_setting

class Unit:
    def __init__(self,system):
        self.system = system
        self.speed_acronym = None
        self.speed_index = None
        self.pressure_acronym = None
        self.temperature_acronym = None
        self.altitude_acronym = None
        self.update()
        
    def update(self):
        self.language = access_setting("language")
        self.set_speed_acronym()
        self.set_speed_index()
        self.set_pressure_acronym()
        self.set_temperature_acronym()
        self.set_altitude_acronym()
        
    def set_speed_acronym(self):
        if self.system == 'METRIC':
            if self.language == 'EN':
                self.speed_acronym = 'KPH'
            else:
                self.speed_acronym = 'KMH'
        elif self.system == 'IMPERI.':
            self.speed_acronym = 'MPH'
            
                
    def set_speed_index(self):
        if self.system == 'METRIC':
            self.speed_index = 2
        elif self.system == 'IMPERI.':
            self.speed_index = 1
            
    def set_pressure_acronym(self):
        if self.system == 'METRIC':
            self.pressure_acronym = 'BAR'
        elif self.system == 'IMPERI.':
            self.pressure_acronym = 'PSI'
            
    def set_temperature_acronym(self):
        if self.system == 'METRIC':
            self.temperature_acronym = 'C'
        elif self.system == 'IMPERI.':
            self.temperature_acronym = 'F'
            
    def set_altitude_acronym(self):
        if self.system == 'METRIC':
            self.altitude_acronym = 'M'
        elif self.system == 'IMPERI.':
            self.altitude_acronym = 'FT'
            