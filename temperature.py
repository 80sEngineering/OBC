from math import log

class Temperature:
    def __init__(self, name, adc):
        self.name = name
        self.adc = adc
        self.refresh_rate_adjuster = {'samples': 0, 'sum': 0, 'last_value': None}
        self.threshold = 0
        self.limit_is_active = False

    def formatted_temperature(self, temperature, acronym):
        if temperature is not None:
            if temperature < -50:  # -50C ~= -50F
                return 'NODATA'
            temperature_str = "{:<5.0f}{}".format(temperature, acronym)
        else:
            temperature_str = "{:>6}".format(acronym)
        return temperature_str

    def get_temperature(self, acronym, formatted=False):
        if self.name == "oil":
            adc_voltage = self.adc.read_voltage(0)
            try:
                RNTC = (5000 / adc_voltage) - 1000
            except ZeroDivisionError:
                RNTC = 90000
            A = 1.291780e-3
            B = 2.612878e-4
            C = 1.568296e-7
        
        elif self.name == "out":
            adc_voltage = self.adc.read_voltage(3)
            try:
                RNTC = (adc_voltage * 4700) / (5 - adc_voltage)
            except ZeroDivisionError: 
                RNTC = 10000
            A = 1.327871e-3
            B = 2.297980e-4
            C = 1.375199e-7
        
        elif self.name == "water":
            adc_voltage = self.adc.read_voltage(7)
            try:
                RNTC = (adc_voltage/(5-adc_voltage))*4700
            except ZeroDivisionError:
                RNTC = 90000
            A = 1.51646e-3
            B = 2.397145e-4
            C = 0.20817e-7
        
        elif self.name == 'exhaust':
            temp_C = [25, 50, 100, 150, 200, 400, 600, 800]
            resistance = [220, 240, 275, 313, 350, 488, 620, 740]
            adc_voltage = self.adc.read_voltage(5)
            try:
                RNTC = ((3.33 / adc_voltage) - 1) * 315
            except ZeroDivisionError:
                RNTC = 10

            for i in range(len(resistance) - 1):
                if resistance[i] <= RNTC <= resistance[i + 1]:
                    # Linear interpolation formula
                    T1, T2 = temp_C[i], temp_C[i + 1]
                    R1, R2 = resistance[i], resistance[i + 1]
                    temperature = T1 + (RNTC - R1) * (T2 - T1) / (R2 - R1)
            if RNTC <= resistance[0]:
                temperature = temp_C[0]
            if RNTC >= resistance[-1]:
                temperature = temp_C[-1]
        
        if self.name in ["oil","out","water"]:
            try:
                temperature = 1 / (A + B * log(RNTC) + C * (log(RNTC))**3)
            except:
                temperature = 222
            temperature -= 273.15  # K to C
            
            
        if acronym == "F":
            temperature = (temperature * 1.8) + 32
        
        return self.formatted_temperature(temperature, acronym) if formatted else temperature
    
    def get_averaged_temperature(self,acronym, formatted=True):
        current_temperature = self.get_temperature(acronym, formatted=False)
        self.refresh_rate_adjuster['sum'] += current_temperature
        self.refresh_rate_adjuster['samples'] += 1
        
        if self.refresh_rate_adjuster['samples'] >= 10:  # Adjust sample count for slower refresh
            averaged_temperature = self.refresh_rate_adjuster['sum'] / self.refresh_rate_adjuster['samples']
            self.refresh_rate_adjuster = {'samples': 0, 'sum': 0, 'last_value': averaged_temperature}
        else:
            averaged_temperature = self.refresh_rate_adjuster.get('last_value')
        return self.formatted_temperature(averaged_temperature, acronym) if formatted else averaged_temperature





