import os
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
from machine import UART, Pin
import utime
import json
from onboard_led import led, flash_led
from my_gps_utils import GPS
from my_epaper_utils import EPD
import pico_socket_server as pss

# GPS
gps = GPS(UART(0, tx=Pin(0), rx=Pin(1), baudrate=9600), debug=False)

# e-Paper
epd = EPD()

# LED event listener
LED_EVENT = asyncio.Event()
async def led_listener():
    while 1:
        await LED_EVENT.wait()
        await flash_led()
        LED_EVENT.clear()

# Program states
IDLE = 'IDLE'
TRACKING = 'TRACKING'
STOPPING = 'STOPPING'
# Current state
CURR_STATE = IDLE
# change current state
def change_state(newState):
    global CURR_STATE
    CURR_STATE = newState
    print('State change:', newState)

# track JSON data
with open('tracks.json', 'r') as f:
    tracks_json = json.load(f)
def dump_tracks_json():
    with open('tracks.json', 'w') as f:
        json.dump(tracks_json, f)


### Main functionality ###

TRAIL_WIDTH = 1 # 1-5, in meters
async def change_trail_width():
    recording_interrupted = True if CURR_STATE == TRACKING else False
    if recording_interrupted:
        stop_recording_trail()
    # this function intentionally uses blocking sleep statements
    global TRAIL_WIDTH
    led.on()
    utime.sleep(0.5)
    def indicate_width():
        print('Trail width:', TRAIL_WIDTH)
        for i in range(TRAIL_WIDTH):
            led.off()
            utime.sleep(0.15)
            led.on()
            utime.sleep(0.15)
        utime.sleep(max(0.2, 0.5-TRAIL_WIDTH/10))
    indicate_width()
    while 1:
        if epd.key0.value() == 0:
            TRAIL_WIDTH -= 1
            indicate_width()
        elif epd.key1.value() == 0:
            led.off()
            utime.sleep(1)
            break
        elif epd.key2.value() == 0:
            TRAIL_WIDTH += 1
            indicate_width()
    if recording_interrupted:
        asyncio.create_task(start_recording_trail())

async def toggle_trail_recording():
    if CURR_STATE == IDLE:
        asyncio.create_task(start_recording_trail())
    else:
        asyncio.create_task(stop_recording_trail())

async def start_recording_trail(log_description=''):
    if CURR_STATE != IDLE:
        return
    led.on()
    print('Recording new trail')
    await gps.update(3) # update gps and let app return html page
    change_state(TRACKING)
    led.off()

    # create log
    log_description = log_description.strip().replace('+', '-') + '_'
    log_filename = f'tracks/TMC_{log_description}{gps.time()}.csv'
    print('opening new log:', log_filename)
    with open(log_filename, 'w') as log:
        log.write('time,latitude,longitude,satellites visible,pdop\n')
    
    # edit tracks.json
    tracks_json[log_filename] = {'width': TRAIL_WIDTH, 'time': gps.time()}
    dump_tracks_json()
    
    # start tracking
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
            epd.run_in_thread(epd.gps_debug, (gps,))

        # delay
        if CURR_STATE == STOPPING:
            change_state(IDLE)
            break
        await asyncio.sleep(2)

async def stop_recording_trail():
    led.on()
    if CURR_STATE != TRACKING:
        return
    change_state(STOPPING)
    while CURR_STATE != IDLE:
        await asyncio.sleep(0.1)
    # epaper
    # TODO

    # finish
    led.off()


### Web app ###

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
        asyncio.create_task(start_recording_trail(paramDict['filename']))
    return pss.redirect('/')
app.add_route('/track', 'post', track)

async def view_tracks(request: pss.Request):
    downloadPage = pss.get_html_template('download.html')
    filenames = [file for file in os.listdir('tracks')]
    downloadPage = downloadPage.replace('FILENAMES', ','.join(filenames))
    return pss.generate_response(body=downloadPage)
app.add_route('/view_tracks', 'GET', view_tracks)

async def download(request: pss.Request):
    filename = request.args["filename"].replace('%20', ' ')
    fileData = None
    with open(f'tracks/{filename}', 'r') as f:
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
    await flash_led()
    asyncio.create_task(epd.manage_threads())
    epd.run_in_thread(epd.initialize, (
        toggle_trail_recording, # key0_func
        change_trail_width, # key1_func
        None # key2_func
    ))
    await gps.initialize()
    asyncio.create_task(led_listener())
    asyncio.create_task(epd.key_listener())
    print('e-Paper key listener ready!')
    server = await asyncio.start_server(app.server_callback, '0.0.0.0', 80, backlog=1)
    print(f'Server running on port 80')
    led.on()
    await server.wait_closed() # serve forever

# start server
asyncio.run(main())