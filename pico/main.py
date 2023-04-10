import os
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import gc
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


### Main functionality ###

map_properties = {
    'bounds': None,
    'zoom': {
        'levels': [200, 400, 'fit'],
        'current': 2 # current zoom level, zero indexed
    }
}

def save_tracks_json():
    with open('tracks.json', 'w') as f:
        json.dump(map_properties['tracks'], f)

def save_junctions_json():
    with open('junctions.json', 'w') as f:
        json.dump({'junctions': map_properties['junctions']}, f)

def save_markers_json():
    with open('markers.json', 'w') as f:
        json.dump({'markers': map_properties['markers']}, f)

with open('tracks.json', 'r') as f:
    tracks_json = json.load(f)
    tracks = os.listdir('tracks')
    for track in tracks_json.keys():
        if track not in tracks:
            tracks_json.pop(track)
    map_properties['tracks'] = tracks_json
    save_tracks_json()

with open('junctions.json', 'r') as f:
    map_properties['junctions'] = json.load(f)['junctions']

with open('markers.json', 'r') as f:
    map_properties['markers'] = json.load(f)['markers']

async def add_junction():
    print('Adding junction')
    await gps.update(3, led)
    lat, long = gps.latlong()
    map_properties['junctions'].append({'lat': lat, 'long': long})
    save_junctions_json()
    print('Number of junctions:', len(map_properties['junctions']))

async def delete_junction():
    print('Deleting junction')
    await gps.update(3, led)
    currLatLong = gps.latlong()
    minDist = 50 # meters
    index = -1
    for i, junction in enumerate(map_properties['junctions']):
        junctionLatLong = (junction['lat'], junction['long'])
        dist = gps.dist(currLatLong, junctionLatLong)
        if dist < minDist:
            minDist = dist
            index = i
    if index != -1:
        map_properties['junctions'].pop(index)
        save_junctions_json()
    print('Number of junctions:', len(map_properties['junctions']))

async def add_marker(text):
    print('Adding marker')
    await gps.update(3, led)
    lat, long = gps.latlong()
    map_properties['markers'].append({'lat': lat, 'long': long, 'text': text})
    save_markers_json()
    print('Number of markers:', len(map_properties['markers']))

async def delete_marker():
    print('Deleting nearest marker')
    await gps.update(3, led)
    currLatLong = gps.latlong()
    minDist = 50 # meters
    index = -1
    for i, marker in enumerate(map_properties['markers']):
        markerLatLong = (marker['lat'], marker['long'])
        dist = gps.dist(currLatLong, markerLatLong)
        if dist < minDist:
            minDist = dist
            index = i
    if index != -1:
        print('Deleting', map_properties['markers'][index])
        map_properties['markers'].pop(index)
        save_markers_json()
    else:
        print('No marker found nearby')

async def view_markers():
    print('Viewing nearby markers')
    await gps.update(3, led)
    currLatLong = gps.latlong()
    search_range = 100 # meters
    markers = []
    for marker in map_properties['markers']:
        markerLatLong = (marker['lat'], marker['long'])
        if gps.dist(currLatLong, markerLatLong) < search_range:
            markers.append(marker)
    epd.run_in_thread(epd.view_markers, (gps, markers, search_range))

async def update_map_properties():
    print('Updating map properties')
    map_properties['bounds'] = None
    tracks = os.listdir('tracks')
    for track in tracks:
        # figure out which columns are which
        latCol = None
        longCol = None
        with open(f'tracks/{track}', 'r') as f:
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
            for i,line in enumerate(f):
                if line.strip() == '':
                    break
                parts = line.split(',')
                lat = float(parts[latCol])
                long = float(parts[longCol])
                
                # set initial map boundaries
                if map_properties['bounds'] is None:
                    map_properties['bounds'] = {}
                    map_properties['bounds']['top'] = lat
                    map_properties['bounds']['bottom'] = lat
                    map_properties['bounds']['left'] = long
                    map_properties['bounds']['right'] = long
                
                # NOTE latitude is horizontal, longitude is vertical
                # update map properties
                if lat > map_properties['bounds']['top']:
                    map_properties['bounds']['top'] = lat
                if lat < map_properties['bounds']['bottom']:
                    map_properties['bounds']['bottom'] = lat
                if long < map_properties['bounds']['left']:
                    map_properties['bounds']['left'] = long
                if long > map_properties['bounds']['right']:
                    map_properties['bounds']['right'] = long

                if i%10 == 0:
                    await asyncio.sleep(0.01)
        await asyncio.sleep(0.01)

    # set additional map properties
    map_properties['bounds']['top'] = gps.latToMeters(map_properties['bounds']['top'])
    map_properties['bounds']['bottom'] = gps.latToMeters(map_properties['bounds']['bottom'])
    map_properties['bounds']['left'] = gps.longToMeters(map_properties['bounds']['left'])
    map_properties['bounds']['right'] = gps.longToMeters(map_properties['bounds']['right'])
    map_properties['height'] = (map_properties['bounds']['top']-map_properties['bounds']['bottom'])
    map_properties['width'] = (map_properties['bounds']['right']-map_properties['bounds']['left'])

CURR_TRAIL_WIDTH = 1 # 1-5, in meters
async def change_trail_width():
    recording_interrupted = True if CURR_STATE == TRACKING else False
    if recording_interrupted:
        await stop_recording_trail()
    # this function intentionally uses blocking sleep statements
    global CURR_TRAIL_WIDTH
    utime.sleep(0.3)
    led.on()
    utime.sleep(0.3)
    def indicate_width():
        print('Trail width:', CURR_TRAIL_WIDTH)
        for i in range(CURR_TRAIL_WIDTH):
            led.off()
            utime.sleep(0.15)
            led.on()
            utime.sleep(0.15)
        utime.sleep(max(0.2, 0.5-CURR_TRAIL_WIDTH/10))
    indicate_width()
    while 1:
        if epd.key0.value() == 0:
            CURR_TRAIL_WIDTH = max(1, CURR_TRAIL_WIDTH - 1)
            indicate_width()
        elif epd.key1.value() == 0:
            led.off()
            utime.sleep(1)
            break
        elif epd.key2.value() == 0:
            CURR_TRAIL_WIDTH += 1
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
    change_state(TRACKING)
    await gps.update(3)
    led.off()

    # create log
    log_description = log_description.strip().replace('+', '-') + '_'
    log_filename = f'TMC_{log_description}{gps.time()}.csv'
    print('Opening new track log:', log_filename)
    with open('tracks/'+log_filename, 'w') as log:
        log.write('time,latitude,longitude,satellites visible,pdop\n')
    
    # edit tracks.json
    map_properties['tracks'][log_filename] = {'width': CURR_TRAIL_WIDTH, 'markers': []}
    save_tracks_json()
    
    # start tracking
    startTime = gps.time()
    epaperDrawInterval = 20 # seconds
    epaperDrawTime = gps.time() - epaperDrawInterval - 1
    lastPointTime = gps.time()
    numPointsTotal = 0
    newPoints = 0
    while 1:
        # update and log
        await gps.update(2, led)
        lat, long = gps.latlong()
        satellitesVisible = len(gps.reader.satellites_visible())
        pdop = gps.reader.pdop
        logEntry = f'{gps.time()},{lat},{long},{satellitesVisible},{pdop}\n'
        print(logEntry)
        with open('tracks/'+log_filename, 'a') as log:
            log.write(logEntry)
        lastPointTime = gps.time()
        numPointsTotal += 1
        newPoints += 1

        # write info to epaper
        if gps.time() - epaperDrawTime > epaperDrawInterval:
            epaperDrawTime = gps.time()
            recordingDuration = gps.time()-startTime
            epd.run_in_thread(epd.display_tracking_info, (gps.timeFormatted(), recordingDuration, gps.time()-lastPointTime, newPoints, numPointsTotal, CURR_TRAIL_WIDTH))
            newPoints = 0

        # delay
        if CURR_STATE == STOPPING:
            change_state(IDLE)
            break
        await asyncio.sleep(1)

async def stop_recording_trail():
    led.on()
    if CURR_STATE != TRACKING:
        return
    print('Stopping trail recording')
    change_state(STOPPING)
    while CURR_STATE != IDLE:
        await asyncio.sleep(0.1)
    asyncio.create_task(display_trails())
    led.off()

async def change_zoom_level():
    currZoomIndex = map_properties['zoom']['current']
    map_properties['zoom']['current'] = (currZoomIndex + 1) % len(map_properties['zoom']['levels'])
    print('Zoom:', map_properties['zoom']['levels'][map_properties['zoom']['current']])

async def display_trails():
    tracks = os.listdir('tracks')
    if len(tracks) == 0:
        print("No tracks recorded yet, can't display trails")
        return
    
    finished_flag = asyncio.ThreadSafeFlag()
    while CURR_STATE == IDLE:
        await update_map_properties()
        gc.collect()
        
        # draw trails
        await gps.update(3)
        print('Displaying recorded trails on e-Paper')
        epd.run_in_thread(epd.draw_trails, (gps, map_properties, finished_flag))
        await finished_flag.wait()


### Web app ###

app = pss.App()

async def approute_home(request: pss.Request):
    body = pss.get_html_template('home.html')
    body = body.replace('CURR_STATE', CURR_STATE)
    return pss.generate_response(title='TMC Home', body=body)
app.add_route('/', 'GET', approute_home)

async def approute_track(request: pss.Request):
    form = dict((param.split('=')[0], param.split('=')[1]) for param in request.body.split('&'))
    if 'stop' in form.keys():
        await stop_recording_trail()
    else:
        asyncio.create_task(start_recording_trail(form['filename']))
    return pss.redirect('/')
app.add_route('/track', 'POST', approute_track)

async def approute_marker(request: pss.Request):
    form = dict((param.split('=')[0], param.split('=')[1]) for param in request.body.split('&'))
    if 'delete' in form.keys():
        await delete_marker()
    else:
        text = form['marker-text'].replace('+', ' ').strip()
        await add_marker(text)
    return pss.redirect('/')
app.add_route('/marker', 'POST', approute_marker)

async def approute_view_tracks(request: pss.Request):
    downloadPage = pss.get_html_template('download.html')
    filenames = [file for file in os.listdir('tracks')]
    downloadPage = downloadPage.replace('FILENAMES', ','.join(filenames))
    return pss.generate_response(body=downloadPage)
app.add_route('/view_tracks', 'GET', approute_view_tracks)

async def approute_download(request: pss.Request):
    filename = request.args["filename"].replace('%20', ' ')
    fileData = None
    with open(f'tracks/{filename}', 'r') as f:
        fileData = f.read()
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
    }
    return pss.generate_response(html=fileData, response_headers=headers)
app.add_route('/download', 'GET', approute_download)

async def approute_loc(request: pss.Request):
    await gps.update(2, led)
    lat, long = gps.latlong()
    latlong = f'{lat},{long}'
    link = f'https://www.google.com/maps/search/{latlong}'
    atag = f'<a href="{link}" target="_blank">{latlong}</a>'
    return pss.generate_response(body=atag)
app.add_route('/loc', 'GET', approute_loc)

async def approute_debug(request: pss.Request):
    await gps.update(3, led)
    debugInfo = gps.getDebugInfo().replace('\n', '<br>')
    body = f'''
        <h2>Debugging info</h2>
        {debugInfo}
    '''
    return pss.generate_response(body=body)
app.add_route('/debug', 'get', approute_debug)


# main
async def main():
    await flash_led()

    # create epaper thread manager and initialize epd
    asyncio.create_task(epd.manage_threads())
    epd.run_in_thread(epd.initialize, (
        toggle_trail_recording, # key0_shortpress_func
        change_trail_width, # key0_longpress_func
        add_junction, # key1_shortpress_func
        delete_junction, # key1_longpress_func
        change_zoom_level, # key2_shortpress_func
        view_markers # key2_longpress_func
    ))
    
    # wait while initializing gps
    await gps.initialize()

    # display trails while idling
    asyncio.create_task(display_trails())
    
    # start listening for epd key presses
    asyncio.create_task(epd.key_listener())
    print('e-Paper key listener ready!')
    
    # start web server
    server = await asyncio.start_server(app.server_callback, '0.0.0.0', 80, backlog=1)
    print(f'Server running on port 80')
    led.on()
    await server.wait_closed() # serve forever

# start server
asyncio.run(main())