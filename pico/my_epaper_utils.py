from machine import Pin
from _thread import start_new_thread
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import utime
from epaper import EPD_2in7
from my_gps_utils import GPS
from onboard_led import flash_led

class EPD():
    def __init__(self):
        self.epd = None
        self._epd_thread_queue = []
        self.key0 = Pin(15, Pin.IN, Pin.PULL_UP)
        self.key1 = Pin(17, Pin.IN, Pin.PULL_UP)
        self.key2 = Pin(2,  Pin.IN, Pin.PULL_UP)
        self._key0_func = None
        self._key1_func = None
        self._key2_func = None
        self._EPD_READY = asyncio.Event()
        self._EPD_READY.set()

    def initialize(self, key0_func, key1_func, key2_func): # functions should be async
        self._key0_func = key0_func
        self._key1_func = key1_func
        self._key2_func = key2_func
        self.epd = EPD_2in7()
        print('e-Paper ready!')
        
    async def manage_threads(self):
        def thread_func(func, args):
            self._EPD_READY.clear()
            func(*args)
            self._EPD_READY.set()
        while 1:
            if len(self._epd_thread_queue) == 0:
                await asyncio.sleep(0.2)
                continue
            await self._EPD_READY.wait()
            await asyncio.sleep(0.1) # give time for thread to exit
            func, args = self._epd_thread_queue.pop(0)
            print('Running e-paper function in thread. Queue length:', len(self._epd_thread_queue))
            EPD_THREAD = start_new_thread(thread_func, (func, args))

    def run_in_thread(self, func: function, args=tuple()):
        self._epd_thread_queue.append((func, args))
        print('Added function to e-paper thread queue of length', len(self._epd_thread_queue))

    async def key_listener(self):
        while 1:
            if self.key0.value() == 0:
                print('Key 0 pressed')
                await flash_led(3)
                asyncio.create_task(self._key0_func())
            if self.key1.value() == 0:
                print('Key 1 pressed')
                await flash_led(3)
                asyncio.create_task(self._key1_func())
            if self.key2.value() == 0:
                print('Key 2 pressed')
                await flash_led(3)
                asyncio.create_task(self._key2_func())
            await asyncio.sleep(0.1)


    ### Miscellaneous functions ###
    def write_text(self, text):
        h = 5
        self.epd.image4Gray.fill(0xff)
        outputLines = text.split('\n')
        for i, line in enumerate(outputLines):
            self.epd.image4Gray.text(line, 5, h, self.epd.black)
            h += 13
        self.epd.EPD_2IN7_4Gray_Display(self.epd.buffer_4Gray)

    # write gps debug info to display
    def gps_debug(self, gps: GPS):
        output = gps.getDebugInfo()
        print('drawing debug info on e-Paper')
        h = 5
        self.epd.image4Gray.fill(0xff)
        for i, line in enumerate(output.split('\n')):
            for part in line.split(': '):
                self.epd.image4Gray.text(part, 5, h, self.epd.black)
                h += 13
        self.epd.EPD_2IN7_4Gray_Display(self.epd.buffer_4Gray)

    # display tracking information while recording trails
    def display_tracking_info(self, filename, currTime, timeSinceLastPoint, newPoints, numPointsTotal, trailWidth):
        h=5
        self.epd.image4Gray.fill(0xff)
        output = 'Filename\n'
        output += filename + '\n'
        output += 'Current epoch time\n'
        output += currTime + '\n'
        output += 'Time since last point\n'
        output += str(timeSinceLastPoint) + '\n'
        output += '# of new points\n'
        output += str(newPoints) + '\n'
        output += 'Total # of points\n'
        output += str(numPointsTotal) + '\n'
        output += 'Current trail width\n'
        output += str(trailWidth)
        for i, line in enumerate(output.split('\n')):
            if i%2:
                self.epd.image4Gray.text(line, 5, h, self.epd.darkgray)
            else:
                self.epd.image4Gray.text(line, 5, h, self.epd.black)
            h += 13
        self.epd.EPD_2IN7_4Gray_Display(self.epd.buffer_4Gray)