import os
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
from machine import UART, Pin
from _thread import start_new_thread
from onboard_led import led, flash_led
from epaper import EPD_2in7
from gpsUtils import GPS
import picoSocketServer as pss

flash_led()

# init e-Paper
KEY0_EVENT = asyncio.Event()
KEY1_EVENT = asyncio.Event()
KEY2_EVENT = asyncio.Event()
async def epaper_key_listener():
    key0 = Pin(15, Pin.IN, Pin.PULL_UP)
    key1 = Pin(17, Pin.IN, Pin.PULL_UP)
    key2 = Pin(2,  Pin.IN, Pin.PULL_UP)
    async def onPress():
        flash_led(3)
        await asyncio.sleep(1)
    while 1:
        if key0.value() == 0:
            KEY0_EVENT.set()
            print('Key 0 pressed')
            await onPress()
            KEY0_EVENT.clear()
        if key1.value() == 0:
            KEY1_EVENT.set()
            print('Key 1 pressed')
            await onPress()
            KEY1_EVENT.clear()
        if key2.value() == 0:
            KEY2_EVENT.set()
            print('Key 2 pressed')
            await onPress()
            KEY2_EVENT.clear()
        await asyncio.sleep(0.1)
epd = None
def init_epaper():
    global epd
    epd = EPD_2in7()
    print('e-Paper ready')
start_new_thread(init_epaper, ())

# create GPS
gps = GPS(UART(0, tx=Pin(0), rx=Pin(1), baudrate=9600), debug=False)

# state vars
IDLE = 'IDLE'
TRACKING = 'TRACKING'
STOPPING = 'STOPPING'
# Current state
CURR_STATE = IDLE
# to change current state
def changeState(newState):
    global CURR_STATE
    CURR_STATE = newState
    print('State change:', newState)

# LED event listener
LED_EVENT = asyncio.Event()
async def led_listener():
    while 1:
        await LED_EVENT.wait()
        flash_led()
        LED_EVENT.clear()

# write gps debug info to ePaper
def ePaper_debug():
    output = gps.getDebugInfo()
    print('drawing debug info on e-Paper')
    h = 5
    epd.image4Gray.fill(0xff)
    outputLines = output.split('\n')
    for i, line in enumerate(outputLines):
        for part in line.split(': '):
            epd.image4Gray.text(part, 5, h, epd.black)
            h += 13
    epd.EPD_2IN7_4Gray_Display(epd.buffer_4Gray)

# start recording new trail
async def record_new_trail(log_description):
    changeState(TRACKING)
    led.off()
    log_description = log_description.strip().replace('+', '-')
    log_filename = f'logs/TMC_{log_description}_{gps.time()}.csv'
    print('opening new log:', log_filename)
    await gps.update(3) # let app return html page
    with open(log_filename, 'w') as log:
        log.write('time,latitude,longitude,satellites visible,pdop\n')
    epaperDrawInterval = 30 # seconds
    start = gps.time() - epaperDrawInterval - 1
    while 1:
        # update and log
        await gps.update(1)
        lat, long = gps.latlong()
        satellitesVisible = len(gps.reader.satellites_visible())
        pdop = gps.reader.pdop
        logEntry = f'{gps.time()},{lat},{long},{satellitesVisible},{pdop}\n'
        print(logEntry)
        with open(log_filename, 'a') as log:
            log.write(logEntry)

        # trigger led event
        LED_EVENT.set()

        # write info to epaper
        if gps.time() - start > epaperDrawInterval:
            start = gps.time()
            start_new_thread(ePaper_debug, ())

        # delay
        if CURR_STATE == STOPPING:
            changeState(IDLE)
            break
        await asyncio.sleep(2)

async def stop_recording_trail():
    if CURR_STATE != IDLE:
        changeState(STOPPING)
        while CURR_STATE != IDLE:
            await asyncio.sleep(0.1)

# functions to run when keys are pressed
async def key0_listener():
    await KEY0_EVENT.wait()
    await stop_recording_trail()
    
async def key1_listener():
    await KEY1_EVENT.wait()
    asyncio.create_task(record_new_trail(''))
    
async def key2_listener():
    await KEY2_EVENT.wait()
    await stop_recording_trail()


# web app functions
app = pss.App()

async def home(request: pss.Request):
    body = pss.get_html_template('home.html')
    body = body.replace('CURR_STATE', CURR_STATE)
    return pss.generate_response(title='TMC Home', body=body)
app.add_route('/', 'GET', home)

async def track(request: pss.Request):
    paramDict = dict((param.split('=')[0], param.split('=')[1]) for param in request.body.split('&'))
    if 'stop' in paramDict.keys():
        await stop_recording_trail()
    else:
        asyncio.create_task(record_new_trail(paramDict['filename']))
    return pss.redirect('/')
app.add_route('/track', 'post', track)

async def view_tracks(request: pss.Request):
    downloadPage = pss.get_html_template('download.html')
    filenames = [file for file in os.listdir('logs')]
    downloadPage = downloadPage.replace('FILENAMES', ','.join(filenames))
    return pss.generate_response(body=downloadPage)
app.add_route('/view_tracks', 'GET', view_tracks)

async def download(request: pss.Request):
    print(request.args)
    filename = request.args["filename"].replace('%20', ' ')
    fileData = None
    with open(f'logs/{filename}', 'r') as f:
        fileData = f.read()
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
    }
    return pss.generate_response(html=fileData, response_headers=headers)
app.add_route('/download', 'GET', download)

async def loc(request: pss.Request):
    await gps.update(2, led)
    lat, long = gps.latlong()
    latlong = f'{lat},{long}'
    link = f'https://www.google.com/maps/search/{latlong}'
    atag = f'<a href="{link}" target="_blank">{latlong}</a>'
    return pss.generate_response(body=atag)
app.add_route('/loc', 'GET', loc)

async def debug(request: pss.Request):
    await gps.update(3, led)
    debugInfo = gps.getDebugInfo().replace('\n', '<br>')
    body = f'''
        <h2>Debugging info</h2>
        {debugInfo}
    '''
    return pss.generate_response(body=body)
app.add_route('/debug', 'get', debug)


# main
async def main():
    await gps.initialize()
    asyncio.create_task(led_listener())
    asyncio.create_task(epaper_key_listener())
    asyncio.create_task(key0_listener())
    asyncio.create_task(key1_listener())
    asyncio.create_task(key2_listener())
    server = await asyncio.start_server(app.server_callback, '0.0.0.0', 80, backlog=1)
    print(f'Server running on port 80')
    led.on()
    await server.wait_closed() # serve forever

# start server
asyncio.run(main())