import os
from machine import Pin
import utime
from _thread import start_new_thread
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import gc
import framebuf
from epaper import EPD_2in7
from my_gps_utils import GPS
from onboard_led import led, flash_led
from file_utils import OpenFileSafely, TrackReader, file_exists

class EPD():
    def __init__(self):
        self.epd = None
        self.width = 176
        self.height = 264
        self.__epd_thread_queue = []
        self.key0 = Pin(15, Pin.IN, Pin.PULL_UP)
        self.key1 = Pin(17, Pin.IN, Pin.PULL_UP)
        self.key2 = Pin(2,  Pin.IN, Pin.PULL_UP)
        self.__key0_shortpress_func = None
        self.__key1_shortpress_func = None
        self.__key2_shortpress_func = None
        self.__EPD_READY = asyncio.Event()
        self.__EPD_READY.set()

    def initialize(self, key0_shortpress_func, key0_longpress_func, key1_shortpress_func, key1_longpress_func, key2_shortpress_func, key2_longpress_func): # functions should be async
        self.__key0_shortpress_func = key0_shortpress_func
        self._key0_longpress_func = key0_longpress_func
        self.__key1_shortpress_func = key1_shortpress_func
        self._key1_longpress_func = key1_longpress_func
        self.__key2_shortpress_func = key2_shortpress_func
        self._key2_longpress_func = key2_longpress_func
        self.epd = EPD_2in7()
        print('e-Paper ready!')
        
    async def manage_threads(self):
        async def async_thread_func(func, args):
            self.__EPD_READY.clear()
            await func(*args)
            self.__EPD_READY.set()
        def sync_thread_func(func, args):
            self.__EPD_READY.clear()
            func(*args)
            self.__EPD_READY.set()
        while 1:
            if len(self.__epd_thread_queue) == 0:
                await asyncio.sleep(0.2)
                continue
            await self.__EPD_READY.wait()
            await asyncio.sleep(0.1) # give time for thread to exit
            func, args, is_async = self.__epd_thread_queue.pop(0)
            print('Running e-paper function in thread. Queue length:', len(self.__epd_thread_queue))
            if is_async:
                start_new_thread(asyncio.create_task, (async_thread_func(func, args),))
            else:
                start_new_thread(sync_thread_func, (func, args))

    # priority argument should only be used by functions in the EPD class. It is used
    # to make sure write_buffer_to_display() is called directly after running an EPD function
    def run_in_thread(self, func: function, args=tuple(), is_async=True, priority=False):
        queue_obj = (func, args, is_async)
        if priority:
            self.__epd_thread_queue.insert(0, queue_obj)
        else:
            self.__epd_thread_queue.append(queue_obj)
        print('Added function to e-paper thread queue of length', len(self.__epd_thread_queue))

    async def key_listener(self):
        sleepInterval = 0.3
        while 1:
            
            if self.key0.value() == 0:
                print('Key 0 pressed')
                await flash_led(3)
                if self.key0.value() == 0:
                    # run long press task
                    utime.sleep(sleepInterval)
                    await flash_led(3)
                    asyncio.create_task(self._key0_longpress_func())
                else:
                    # run short press task
                    asyncio.create_task(self.__key0_shortpress_func())
                    
            if self.key1.value() == 0:
                print('Key 1 pressed')
                await flash_led(3)
                if self.key1.value() == 0:
                    # run long press task
                    utime.sleep(sleepInterval)
                    await flash_led(3)
                    asyncio.create_task(self._key1_longpress_func())
                else:
                    # run short press task
                    asyncio.create_task(self.__key1_shortpress_func())
                    
            if self.key2.value() == 0:
                print('Key 2 pressed')
                await flash_led(3)
                if self.key2.value() == 0:
                    # run long press task
                    utime.sleep(sleepInterval)
                    await flash_led(3)
                    asyncio.create_task(self._key2_longpress_func())
                else:
                    # run short press task
                    asyncio.create_task(self.__key2_shortpress_func())
            await asyncio.sleep(sleepInterval)


    ### Miscellaneous functions ###

    # use buttons to select something
    def button_select(self, initial_val: int, min_val: int = 1, max_val: int = 10, on_change_callback: function = lambda x: x):
        # this function is intentionally asyncio-blocking
        curr_val = initial_val
        utime.sleep(0.5)
        led.on()
        utime.sleep(0.3)
        def indicate_curr_val():
            for i in range(curr_val):
                led.off()
                utime.sleep(0.15)
                led.on()
                utime.sleep(0.15)
            on_change_callback(curr_val)
            utime.sleep(max(0.2, 0.5-curr_val/10))
        indicate_curr_val()
        while 1:
            if self.key0.value() == 0:
                curr_val = max(min_val, curr_val - 1)
                indicate_curr_val()
            elif self.key1.value() == 0:
                led.off()
                utime.sleep(0.5)
                return curr_val
            elif self.key2.value() == 0:
                curr_val = min(max_val, curr_val + 1)
                indicate_curr_val()

    # Write epd buffer to the display, takes around ~6 seconds
    # You may pass an asyncio flag to the finished_flag argument if desired
    # Case 1: function is called from an AYSNCHRONOUS function
    #   Asyncio tasks on CORE0 will be blocked until function finishes
    # Case 2: function is called from a SYNCHRONOUS function
    #   Case 2a: If called from CORE0, will block asyncio tasks until finished
    #   Case 2b: If called from CORE1, will not block CORE0 asyncio tasks
    # To avoid blocking asyncio tasks: use self.run_in_thread(self.write_buffer_to_display)
    def write_buffer_to_display(self, finished_flag: asyncio.ThreadSafeFlag=None):
        self.epd.EPD_2IN7_4Gray_Display(self.epd.buffer_4Gray)
        if finished_flag is not None:
            finished_flag.set()

    # display tracking information while recording trails
    async def display_tracking_info(self, currTime, recordingDuration, timeSinceLastPoint, newPoints, numPointsTotal, trailWidth):
        self.run_in_thread(self.write_buffer_to_display, is_async=False, priority=True)
        h=5
        self.epd.image4Gray.fill(self.epd.white)
        output = 'Current time\n'
        output += currTime + '\n'
        output += 'Recording duration\n'
        output += f'{recordingDuration//60} min and {recordingDuration%60} sec' + '\n'
        output += 'Time since last point\n'
        output += f'{timeSinceLastPoint} seconds' + '\n'
        output += '# of new points\n'
        output += str(newPoints) + '\n'
        output += 'Total # of points\n'
        output += str(numPointsTotal) + '\n'
        output += 'Current trail width\n'
        output += f'{trailWidth} meters'
        for i, line in enumerate(output.split('\n')):
            if i%2:
                self.epd.image4Gray.text(line, 5, h, self.epd.darkgray)
            else:
                self.epd.image4Gray.text(line, 5, h, self.epd.black)
            h += 13

    async def draw_trails(self, gps: GPS, map_properties, finished_flag: asyncio.ThreadSafeFlag):
        self.run_in_thread(self.write_buffer_to_display, args=(finished_flag,), is_async=False, priority=True)
        # transformation functions from (lat, long) to (x, y) coordinates
        currZoom = map_properties['zoom']['levels'][map_properties['zoom']['current']]
        scalingFactor = None
        if currZoom == 'fit':
            mapAspectRatio = map_properties['width'] / map_properties['height']
            displayAspectRatio = self.width / self.height
            if mapAspectRatio > displayAspectRatio:
                scalingFactor = self.width / map_properties['width']
            else:
                scalingFactor = self.height / map_properties['height']
        else:
            scalingFactor = self.width / currZoom

        def scale(lat, long):
            lat = gps.latToMeters(lat)
            long = gps.longToMeters(long)
            y = self.height - (lat - map_properties['bounds']['bottom']) * scalingFactor
            x = (long - map_properties['bounds']['left']) * scalingFactor
            return x, y
        
        currLatlong = gps.latlong()
        currPos = scale(*currLatlong)
        # center map on current coords
        def translate(x, y):
            if currZoom != 'fit':
                x += self.width/2 - currPos[0]
                y += self.height/2 - currPos[1]
            return x, y
        
        def transform(lat, long):
            x, y = scale(lat, long)
            x, y = translate(x, y)
            return int(x), int(y)
        
        # get and draw tracks in subsets by trail width, descending
        # dilate_image is applied after each subset is drawn to achieve drawing line thickness
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
                prev = None
                curr = None
                async for lat, long in TrackReader(track):
                    curr = transform(lat, long)
                    # draw line
                    if prev is not None:
                        # skip if point is too close to prev
                        dist = ((curr[0] - prev[0]) ** 2 + (curr[1] - prev[1]) ** 2) ** (1/2)
                        if dist >= 2:
                            self.epd.image4Gray.line(*prev, *curr, self.epd.black)
                            prev = curr
                    else:
                        prev = curr
                self.epd.image4Gray.line(*prev, *curr, self.epd.black)
                await asyncio.sleep(0)
            if currWidth != 1:
                self.dilate_image(self.epd.black)

        # draw junctions
        for junction in map_properties['junctions']:
            x, y = transform(junction['lat'], junction['long'])
            self.epd.image4Gray.ellipse(x, y, 5, 5, self.epd.lightgray)
            self.epd.image4Gray.text('x', x-3, y-4, self.epd.lightgray)

        # draw markers
        for marker in map_properties['markers']:
            x, y = transform(marker['lat'], marker['long'])
            self.epd.image4Gray.ellipse(x, y, 5, 5, self.epd.darkgray)
            self.epd.image4Gray.text('i', x-4, y-3, self.epd.darkgray)
        
        # draw current position
        currPos = transform(*currLatlong)
        self.epd.image4Gray.line(currPos[0]-4, currPos[1], currPos[0]+4, currPos[1], self.epd.black)
        self.epd.image4Gray.line(currPos[0], currPos[1]-4, currPos[0], currPos[1]+4, self.epd.black)
        self.epd.image4Gray.ellipse(*currPos, 3, 3, self.epd.black)

        # info text
        if currZoom == 'fit':
            currZoom = round(map_properties["width"])
        self.epd.image4Gray.text(f'Map width: {currZoom}m', 5, 5, self.epd.darkgray)

    def dilate_image(self, color):
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

    async def view_markers(self, gps: GPS, markers, finished_flag: asyncio.ThreadSafeFlag):
        self.epd.image4Gray.fill(self.epd.white)
        currLatlong = gps.latlong()
        h = 5
        self.epd.image4Gray.text('-- Markers Near You --', 5, h, self.epd.black)
        for i, marker in enumerate(markers):
            # write marker info header
            # ex: 1) 10m N 88m E [o]
            xDist = round(gps.longToMeters(currLatlong[1] - marker['long']))
            yDist = round(gps.latToMeters(currLatlong[0] - marker['lat']))
            xDirection = 'W' if xDist > 0 else 'E'
            yDirection = 'S' if yDist > 0 else 'N'
            marker_info = f'{i+1}) {abs(xDist)}m {xDirection} {abs(yDist)}m {yDirection}'
            if await file_exists('marker_imgs/'+marker['id']):
                marker_info += ' [o]' # indicate there is an image associated with the marker
            h += 13
            self.epd.image4Gray.text(marker_info, 5, h, self.epd.black)
            # write marker text
            marker_text = marker['text']
            lineLength = 20
            textParts = [marker_text[i:i+lineLength] for i in range(0, len(marker_text), lineLength)]
            for part in textParts:
                h += 13
                self.epd.image4Gray.text(part, 5, h, self.epd.darkgray)
        self.write_buffer_to_display(finished_flag)

    async def view_marker_img(self, marker: str):
        print('viewing marker:', marker['id'])
        buf_index = 0
        chunk_size = 32 # max possible chunk size is 32
        file = 'marker_imgs/'+marker['id']
        if not await file_exists(file):
            print('No image associated with marker ID', marker['id'])
            await flash_led(2)
            return
        async with OpenFileSafely(file, 'rb') as f:
            while 1:
                bytes_buf = f.read(chunk_size)
                if bytes_buf == b'':
                    break
                for i in range(chunk_size):
                    self.epd.buffer_4Gray[buf_index+i] = bytes_buf[i]
                buf_index += chunk_size
        self.epd.image4Gray.text(marker['text'], 5, 5, self.epd.white)

        # display and intentionally block
        self.write_buffer_to_display()
        viewing_duration = 15 # seconds
        utime.sleep(viewing_duration)
