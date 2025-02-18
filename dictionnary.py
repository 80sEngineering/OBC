class Dictionnary:
    def __init__(self,language):
        self.language = language
        self.words = {}
        self.set_words()
    
    def set_words(self):
        if self.language == 'EN':
            self.words= {
                               'HOUR' : 'HOUR',
                               'DATE' : 'DATE',
                               'months' : ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'],
                               'TIMER' : 'TIMER',
                               'LAP' : 'LAP',
                               'READY' : 'READY',
                               'STOP' : 'STOP',
                               'SIGNAL' : 'SIGNAL',
                               'ACCEL' : 'ACCEL',
                               'SPEED' : 'SPEED',
                               'ON' : 'ON',
                               'OFF' : 'OFF',
                               'LIMIT' : 'LIMIT',
                               'KMH' : 'KMH',
                               'DIST' : 'DIST',
                               'RANGE' : 'RANGE',
                               'FUEL' : 'FUEL',
                               'ODO' : 'ODO',
                               'TEMP' : 'TEMP',
                               'MAX' : 'MAX',
                               'VOLT' : 'VOLT',
                               'OIL' : 'OIL',
                               'OUTEMP':'OUTEMP',
                               'ALT' : 'ALT',
                               'HDG' : 'HDG',
                               'G SENS' : 'G SENS',
                               'SET' : 'SET',
                               'LIGHTS' : 'LIGHTS'}
            
        elif self.language == 'FR':
            self.words =  {
                               'HOUR' : 'HEURE',
                               'DATE' : 'DATE',
                               'months' : ['JAN', 'FEV', 'MAR', 'AVR', 'MAI', 'JUN', 'JUL', 'AOU', 'SEP', 'OCT', 'NOV', 'DEC'],
                               'TIMER' : 'CHRONO',
                               'LAP' : 'TOUR',
                               'READY' : 'PRET',
                               'STOP' : 'STOP',
                               'SIGNAL' : 'SIGNAL',
                               'ACCEL' : 'ACCEL',
                               'SPEED' : 'VITES',
                               'ON' : 'ACTIF',
                               'OFF' : 'ETEINT',
                               'LIMIT' : 'LIMITE',
                               'KMH' : 'KMH',
                               'DIST' : 'DIST',
                               'RANGE': 'AUTONO.',
                               'FUEL': 'CARBUR.',
                               'ODO' : 'ODO',
                               'TEMP' : 'TEMP',
                               'MAX' : 'MAX',
                               'VOLT' : 'VOLT',
                               'OIL' : 'HUILE',
                               'OUTEMP': 'TMP.EXT.',
                               'ALT' : 'ALT',
                               'HDG' : 'CAP',
                               'G SENS' : 'G',
                               'SET':'PARAM.',
                               'LIGHTS':'PHARES'
                               }
            
        elif self.language == 'DE':
            self.words = {
                               'HOUR' : 'STUNDE',
                               'DATE' : 'DATUM',
                               'months' : ['JAN', 'FEB', 'MAR', 'APR', 'MAI', 'JUN', 'JUL', 'AUG', 'SEP', 'OKT', 'NOV', 'DEZ'],
                               'TIMER' : 'ZEIT',
                               'LAP' : 'RUNDE',
                               'READY' : 'BEREIT',
                               'STOP' : 'STOP',
                               'SIGNAL' : 'SIGNAL',
                               'ACCEL' : 'BESCHL',
                               'SPEED' : 'GESCHW',
                               'ON' : 'AN',
                               'OFF' : 'AUS',
                               'LIMIT' : 'LIMIT',
                               'KMH' : 'KMH',
                               'DIST' : 'DIST',
                               'RANGE' : 'REICHW.',
                               'FUEL' : 'TANK',
                               'ODO' : 'KM',
                               'TEMP' : 'TEMP',
                               'MAX' : 'MAX',
                               'VOLT' : 'VOLT',
                               'OIL' : 'OL',
                               'OUTEMP': 'A-TEMP',
                               'ALT' : 'HOHE',
                               'HDG' : 'KOMPAS',
                               'G SENS' : 'GKRAFT',
                               'SET':'SET',
                               'LIGHTS':'LICHT',
                
                }
            
    