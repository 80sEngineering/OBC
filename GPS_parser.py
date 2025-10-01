import utime
import math
from memory import access_setting


def _nmea_checksum_ok(sentence: bytes) -> bool:
    # sentence like b"$GPRMC,....*CS\r\n"
    try:
        star = sentence.rfind(b'*')
        if star == -1:
            return False
        cs = int(sentence[star+1:star+3], 16)
        body = sentence[1:star]
        calc = 0
        for b in body:
            calc ^= b
        return calc == cs
    except:
        return False

def _dm_to_degrees(dm, hemi):
    # dm like "4807.038", hemi 'N'/'S' or 'E'/'W'
    if not dm or not hemi:
        return None
    try:
        dm = float(dm)
    except:
        return None
    deg = int(dm // 100)
    minutes = dm - deg * 100
    dec = deg + minutes / 60.0
    if hemi in ('S', 'W'):
        dec = -dec
    return dec

def _knots_to_mph(kn):
    return kn * 1.150779448  # exact enough

def _knots_to_kmh(kn):
    return kn * 1.852

# ----------------- parsed container -----------------

class Parsed:
    def __init__(self):
        self.speed = [0.0, 0.0, 0.0]   # [knots, mph, kmh]
        self.course = 0.0
        self.latitude  = (None,)       # latitude[0] -> decimal degrees
        self.longitude = (None,)       # longitude[0] -> decimal degrees
        self.altitude  = None          # optional (from GGA)
        self.timestamp = 0             # ticks_ms when last valid fix was parsed
        self.fix_time  = 0             # ticks_ms (compat with your uses)

# ----------------- main class -----------------

class GPS_handler:
    def __init__(self, uart):
        self.uart = uart
        self.parsed = Parsed()
        self._has_fix = False          # RMC status == 'A'
        self.previous_place = {'latitude': None, 'longitude': None, 'time': 0}
        self.trip = 0
        
    def has_fix(self):
        return self._has_fix

    def get_GPS_data(self):
        """Read any pending NMEA lines and update parsed fields.
           If we have a fix and >1s since previous_place, update distance/odometer.
        """
        self.read_NMEA()
        if self.has_fix() and self.previous_place['time'] != 0:
            if utime.ticks_diff(self.parsed.fix_time, self.previous_place['time']) > 1000:
                self.get_distance()
        
    def read_NMEA(self):
        while self.uart.any():
            try:
                line = self.uart.readline()
                if not line:
                    break
                if not line.startswith(b'$'):
                    continue
                if not _nmea_checksum_ok(line):
                    continue

                s = line.strip()
                if s[3:6] == b'RMC' or s[2:5] == b'RMC':
                    self._parse_rmc(s)
                elif s[3:6] == b'GGA' or s[2:5] == b'GGA':
                    self._parse_gga(s)
            except (UnicodeError, MemoryError):
                pass

    def _parse_rmc(self, s: bytes):
        # RMC: $GPRMC,hhmmss.sss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,ddmmyy,x.x,a*CS
        # We only need status, lat, N/S, lon, E/W, speed(kn), course
        try:
            body = s[1:s.rfind(b'*')]
            parts = body.split(b',')

            # Talker,RMC at parts[0]
            status = parts[2:3][0] if len(parts) > 2 else b'V'
            self._has_fix = (status == b'A')

            lat = _dm_to_degrees(parts[3].decode(), parts[4:5][0].decode() if len(parts)>4 else '')
            lon = _dm_to_degrees(parts[5].decode(), parts[6:7][0].decode() if len(parts)>6 else '')

            spd_kn = float(parts[7]) if len(parts)>7 and parts[7] else 0.0
            crs    = float(parts[8]) if len(parts)>8 and parts[8] else 0.0

            self.parsed.latitude  = (lat,)
            self.parsed.longitude = (lon,)
            self.parsed.course    = crs
            self.parsed.speed[0]  = spd_kn
            self.parsed.speed[1]  = _knots_to_mph(spd_kn)
            self.parsed.speed[2]  = _knots_to_kmh(spd_kn)

            now = utime.ticks_ms()
            self.parsed.timestamp = now
            if self._has_fix:
                self.parsed.fix_time = now

            # Initialize previous_place on first valid fix
            if self._has_fix and self.previous_place['latitude'] is None and lat is not None and lon is not None:
                self.previous_place['latitude']  = lat
                self.previous_place['longitude']  = lon
                self.previous_place['time'] = now

        except Exception:
            # Ignore malformed RMCs
            pass

    def _parse_gga(self, s: bytes):
        # GGA: $GPGGA,hhmmss.sss,lat,N,lon,E,fix,numsats,hdop,alt,M,geoid,M,...*CS
        try:
            body = s[1:s.rfind(b'*')]
            p = body.split(b',')
            alt = float(p[9]) if len(p) > 9 and p[9] else None
            self.parsed.altitude = alt
            # fix quality p[6] could be used to refine _has_fix, but RMC status is enough for your usage
        except Exception:
            pass
    
    def get_distance(self):
        lat = self.parsed.latitude[0]
        lon = self.parsed.longitude[0]
        if lat is None or lon is None:
            return

        if self.parsed.speed[2] <= 10.0:
            self.previous_place['time'] = self.parsed.fix_time
            return

        prev_lat = self.previous_place['latitude']
        prev_lon = self.previous_place['longitude']
        if prev_lat is None or prev_lon is None:
            self.previous_place['latitude']  = lat
            self.previous_place['longitude']  = lon
            self.previous_place['time'] = self.parsed.fix_time
            return

        # Haversine (meters)
        R = 6371000.0
        phi1 = math.radians(prev_lat)
        phi2 = math.radians(lat)
        dphi = math.radians(lat - prev_lat)
        dl   = math.radians(lon - prev_lon)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        meters = R * c
        km = meters / 1000.0
        self.trip += km
    
       

        # Move the previous point forward
        self.previous_place['latitude']  = lat
        self.previous_place['longitude']  = lon
        self.previous_place['time'] = self.parsed.fix_time
    
    def save_odometer(self):
        odometer_value = access_setting('odometer')
        total = odometer_value + self.trip
        access_setting('odometer', total)
        self.trip = 0
        
    def compass_direction(self):
        """
        Return a 16-wind compass string from current course:
        N, NNE, NE, ENE, E, ESE, SE, SSE, S, SSW, SW, WSW, W, WNW, NW, NNW
        """
        c = self.parsed.course
        if c is None:
            return "---"
        # Normalize and map every 22.5° with a 11.25° offset
        dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                "S","SSW","SW","WSW","W","WNW","NW","NNW"]
        idx = int(((c % 360) + 11.25) / 22.5) % 16
        return dirs[idx]