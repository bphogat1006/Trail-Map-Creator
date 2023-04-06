from machine import Pin
from _thread import start_new_thread
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import gc
import framebuf
from epaper import EPD_2in7
from my_gps_utils import GPS
from onboard_led import flash_led

class EPD():
    def __init__(self):
        self.epd = None
        self.width = 176
        self.height = 264
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
        self.epd.image4Gray.fill(self.epd.white)
        outputLines = text.split('\n')
        for i, line in enumerate(outputLines):
            self.epd.image4Gray.text(line, 5, h, self.epd.black)
            h += 13
        self.self.EPD_2IN7_4Gray_Display(self.epd.buffer_4Gray)

    # write gps debug info to display
    def gps_debug(self, gps: GPS):
        output = gps.getDebugInfo()
        print('drawing debug info on e-Paper')
        h = 5
        self.epd.image4Gray.fill(self.epd.white)
        for i, line in enumerate(output.split('\n')):
            for part in line.split(': '):
                self.epd.image4Gray.text(part, 5, h, self.epd.black)
                h += 13
        self.self.EPD_2IN7_4Gray_Display(self.epd.buffer_4Gray)

    # display tracking information while recording trails
    def display_tracking_info(self, filename, currTime, timeSinceLastPoint, newPointsBuffer, numPointsBufferTotal, trailWidth):
        h=5
        self.epd.image4Gray.fill(self.epd.white)
        output = 'Filename\n'
        output += filename + '\n'
        output += 'Current time\n'
        output += currTime + '\n'
        output += 'Time since last point\n'
        output += str(timeSinceLastPoint) + '\n'
        output += '# of new pointsBuffer\n'
        output += str(newPointsBuffer) + '\n'
        output += 'Total # of pointsBuffer\n'
        output += str(numPointsBufferTotal) + '\n'
        output += 'Current trail width\n'
        output += str(trailWidth)
        for i, line in enumerate(output.split('\n')):
            if i%2:
                self.epd.image4Gray.text(line, 5, h, self.epd.darkgray)
            else:
                self.epd.image4Gray.text(line, 5, h, self.epd.black)
            h += 13
        self.epd.EPD_2IN7_4Gray_Display(self.epd.buffer_4Gray)

    def draw_trails(self, currLatlong, map_properties):
        # transformation function from (lat, long) to (x, y) coordinates
        scalingFactor = None
        mapAspectRatio = map_properties['width'] / map_properties['height']
        displayAspectRatio = self.width / self.height
        if mapAspectRatio > displayAspectRatio:
            scalingFactor = self.width / map_properties['width']
        else:
            scalingFactor = self.height / map_properties['height']
        def transform(lat, long): # lat: 
            y = self.height - (lat - map_properties['bounds']['bottom']) * scalingFactor
            x = (long - map_properties['bounds']['left']) * scalingFactor
            return int(x), int(y)
        
        # get and draw tracks in subsets by trail width, descending
        # dilation is applied after each subset is drawn to achieve drawing line thickness
        tracks = map_properties['tracks'].keys()
        maxWidth = 0
        for track in tracks:
            w = map_properties['tracks'][track]['width']
            if w > maxWidth:
                maxWidth = w
        widthRange = [i for i in range(1, maxWidth+1)]
        widthRange.reverse()
        self.epd.image4Gray.fill(self.epd.white)
        for currWidth in widthRange:
            tracks_subset = [track for track in tracks if map_properties['tracks'][track]['width'] == currWidth]
            # draw tracks
            for track in tracks_subset:
                # figure out which columns are which
                latCol = None
                longCol = None
                with open(f'tracks/{track}') as f:
                    header = f.readline()
                    cols = header.split(',')
                    for i,col in enumerate(cols):
                        if 'latitude' in col:
                            latCol = i
                        elif 'longitude' in col:
                            longCol = i
                    if latCol is None or longCol is None:
                        raise Exception('Unable to parse CSV file:', track)
                    
                    # parse line by line
                    prev = None
                    for line in f:
                        if line.strip() == '':
                            break
                        parts = line.split(',')
                        lat = float(parts[latCol])
                        long = float(parts[longCol])
                        curr = transform(lat, long)
                        if curr[0] > self.width:
                            print(curr)
                        # draw line
                        if prev is not None:
                            # skip if point is redundant or an outlier
                            dist = ((curr[0] - prev[0]) ** 2 + (curr[1] - prev[1]) ** 2) ** (1/2)
                            if dist <= 1:# or dist > 15:
                                continue
                            self.epd.image4Gray.line(*prev, *curr, self.epd.black)
                        prev = curr
            if currWidth != 1:
                self.dilation(self.epd.black)
            gc.collect()
        
        # draw current position
        pos = transform(*currLatlong)
        radius = 3
        self.epd.image4Gray.ellipse(*pos, 3, 3, self.epd.darkgray, True)

        # update display
        self.epd.EPD_2IN7_4Gray_Display(self.epd.buffer_4Gray)

    def dilation(self, color):
        pointsBuffer = []
        def draw_kernel(x, y):
            self.epd.image4Gray.pixel(x+1, y, color)
            self.epd.image4Gray.pixel(x-1, y, color)
            self.epd.image4Gray.pixel(x, y+1, color)
            self.epd.image4Gray.pixel(x, y-1, color)
        for x in range(self.width):
            for y in range(self.height):
                if self.epd.image4Gray.pixel(x, y) != 0b11: # if pixel not white
                    pointsBuffer.append((x, y))
                while len(pointsBuffer) and pointsBuffer[0][0] < x-2:
                    draw_kernel(*pointsBuffer.pop(0))
        for p in pointsBuffer:
            draw_kernel(*p)