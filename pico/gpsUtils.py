from utime import sleep, mktime
from micropyGPS import MicropyGPS

#####################################################
# DO NOT USE GPS METHODS BEFORE CALLING .init() FIRST
#####################################################

class GPS:
    def __init__(self, uart, debug=False):
        self.uart = uart
        self.reader = MicropyGPS()
        self._gotInitialFix = False
        self.debug = debug

    # get serial data from UART
    def _read_UART(self):
        while 1:
            # wait until there's data available to read from uart
            if self.uart.any() == 0:
                if self.debug:
                    print('No data to read from UART')
                sleep(0.1)
                continue
            
            # read uart data
            try:
                data = self.uart.read()
                data = data.decode('ascii')
                data = data.strip()
            except UnicodeError as e:
                if self.debug:
                    print('Unicode Error while decoding GPS buffer')
                sleep(0.1)
                continue
            
            # return data
            if self.debug:
                print(data)
            return data

    # fetch new gps data and update gps.reader
    def update(self, count, led=None):
        if count == 0:
            if led is not None:
                led.off()
            return
        
        if led is not None:
                led.on()
        
        # update gps parser with data
        data = self._read_UART()
        for char in data:
            try:
                self.reader.update(char)
            except Exception as e:
                err = f'Error in micropyGPS.update(): {e}'
                self.logError(err)
        
        # make sure fix was not lost
        if self._gotInitialFix and (self.reader.time_since_fix() == -1 or self.latlong()[0] == 0.0):
            err = 'GPS error: fix was lost!\n' + self.getDebugInfo()
            self.logError(err)
            print('Waiting for GPS fix...')
            # count += 1
        
        # recurse
        if count > 1:
            sleep(1.1)
        self.update(count-1, led)

    # get location fix
    def init(self):
        while self.reader.time_since_fix() == -1:
            print('Waiting for GPS fix...')
            sleep(1.1)
            self.update(1)
        self._gotInitialFix = True
        print('GPS fix obtained')

    # continuously track
    def start_continuous_tracking(self, interval=1.1):
        while 1:
            self.update(1)
            sleep(interval)

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
        output += '\n'
        return output

    # write debugging info to e-Paper
    def start_ePaper_debugging(self, epd, interval=20):
        while 1:
            self.update(1)
            output = self.getDebugInfo()
            if self.debug:
                print(output)
            
            # draw on e-Paper
            print('drawing on e-Paper')
            h = 5
            epd.image4Gray.fill(0xff)
            outputLines = output.split('\n')
            for i, line in enumerate(outputLines):
                for part in line.split(': '):
                    epd.image4Gray.text(part, 5, h, epd.black)
                    h += 13
            epd.EPD_2IN7_4Gray_Display(epd.buffer_4Gray)
            
            # delay
            sleep(interval)

    def getTime(self):
        day, month, year, hour, minute, second = [int(x) for x in list(self.reader.date) + self.reader.timestamp]
        datetime = (year+2000, month, day, hour, minute, second, 0, 0)
        return mktime(datetime)

    def logError(self, err):
        print(err)
        with open('gps_error.log', 'a') as log:
            log.write(f'{self.getTime()}: {err}\n')





