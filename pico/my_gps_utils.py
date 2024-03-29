import utime
from machine import RTC, UART
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
from micropyGPS import MicropyGPS

###########################################################
# DO NOT USE GPS METHODS BEFORE CALLING .initialize() FIRST
###########################################################

class GPS:
    def __init__(self, uart: UART, debug=False):
        self.uart = uart
        self.reader = MicropyGPS()
        self.__gotInitialFix = False
        self.debug = debug
        self.rtc = RTC()
        # other
        self.timezone_diff = 4 # only used for self.timeFormatted()
        self.distBetweenLatitudes = 111190 # NOTE constant for anywhere in the world
        self.distBetweenLongitudes = 85050 # NOTE depends on which latitude you measure at. This is an approximation for latitude 40.1 N

    # get serial data from UART
    async def _read_UART(self):
        while 1:
            # wait until there's data available to read from uart
            if self.uart.any() == 0:
                if self.debug:
                    print('No data to read from UART')
                await asyncio.sleep(0.1)
                continue
            
            # read uart data
            try:
                data = self.uart.read()
                data = data.decode('ascii')
                data = data.strip()
            except UnicodeError as e:
                if self.debug:
                    print('Unicode Error while decoding GPS buffer')
                await asyncio.sleep(0.1)
                continue
            
            # return data
            if self.debug:
                print(data)
            return data

    # fetch new gps data and update gps.reader
    async def update(self, count, led=None):
        if led is not None:
            led.on()
            
        while True:
            if count == 0:
                break
            
            # update gps parser with data
            data = await self._read_UART()
            for char in data:
                try:
                    self.reader.update(char)
                except Exception as e:
                    err = f'Error in micropyGPS.update(): {e}'
            
            # make sure fix was not lost
            if self.__gotInitialFix and \
                    (self.reader.time_since_fix() == -1 or self.latlong()[0] == 0.0 or self.latlong()[1] == 0.0):
                print('Waiting for GPS fix...')
                count += 1
            
            # sleep 1s bc gps outputs at 1Hz, then continue
            if count > 1:
                await asyncio.sleep(1)
            count -= 1
        
        if led is not None:
            led.off()

    # get location fix
    async def initialize(self):
        # wait for fix
        print('Waiting for GPS fix...')
        await self.update(1)
        while self.reader.time_since_fix() == -1:
            await asyncio.sleep(1.1)
            await self.update(1)
        self.__gotInitialFix = True
        await self.update(3)
        # set RTC
        day, month, year, hour, minute, second = [int(x) for x in list(self.reader.date) + self.reader.timestamp]
        datetime = (year+2000, month, day, None, hour, minute, second, 0)
        self.rtc.datetime(datetime)
        print('GPS fix obtained')

    # continuously track
    async def start_continuous_tracking(self, interval=1.1):
        while 1:
            await self.update(1)
            await asyncio.sleep(interval)

    def latlong(self):
        lat = self.reader.latitude
        lat = (lat[0] + lat[1]/60) * (1 if lat[2] == 'N' else -1)
        long = self.reader.longitude
        long = (long[0] + long[1]/60) * (1 if long[2] == 'E' else -1)
        return [lat, long]
            
    # get debugging info
    def getDebugInfo(self):
        # get data from gps parser
        gpsTime = f'{(self.reader.timestamp[0]-5)%12}:{self.reader.timestamp[1]}:{round(self.reader.timestamp[2])}'
        output =  f'time: {gpsTime}\n'
        output += f'clean sentences: {self.reader.clean_sentences}\n'
        output += f'time since last fix: {self.reader.time_since_fix()}\n'
        satellitesVisible = self.reader.satellites_visible()
        output += f'satellites visible: {len(satellitesVisible)} {satellitesVisible}\n'
        output += f'satellites used: {self.reader.satellites_in_use}\n'
        output += f'position dilution: {self.reader.pdop}\n'
        lat, long = self.latlong()
        output += f'lat: {lat}\n'
        output += f'long: {long}\n'
        output += f'speed: {self.reader.speed_string(unit="mph")}\n'
        output += f'direction: {self.reader.compass_direction()}\n'
        return output

    def time(self): # does not account for time zone
        year, month, day, weekday, hour, minute, second, subsecond = self.rtc.datetime()
        datetime = (year, month, day, hour, minute, second, 0, 0)
        return utime.mktime(datetime)
    
    def timeFormatted(self): # accounts for time zone
        year, month, day, weekday, hour, minute, second, subsecond = self.rtc.datetime()
        timeString = f'{month}/{day}/{year}, {(hour-self.timezone_diff)%12}:{minute}:{second}'
        return timeString

    def latToMeters(self, lat):
        return lat * self.distBetweenLatitudes

    def longToMeters(self, long):
        return long * self.distBetweenLongitudes

    def dist(self, latlong1, latlong2): # return distance in meters
        y1, x1 = latlong1
        y2, x2 = latlong2
        return ( self.longToMeters(x1 - x2) ** 2 + self.latToMeters(y1 - y2) ** 2 ) ** 0.5

