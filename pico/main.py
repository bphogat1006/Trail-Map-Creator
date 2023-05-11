import os
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
from machine import UART, Pin, soft_reset
import utime
import json
from onboard_led import led, flash_led
from my_gps_utils import GPS
from my_epaper_utils import EPD
import pico_socket_server as pss
from file_utils import OpenFileSafely, TrackReader, file_exists

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

# map properties
map_properties = {
    'bounds': None,
    'zoom': {
        'levels': ['fit', 200, 400, 800],
        'current': 0 # current zoom level (zero indexed, default is 'fit')
    },
}


### Main functionality ###

async def save_tracks_json():
    async with OpenFileSafely('tracks.json', 'w') as f:
        json.dump(map_properties['tracks'], f)

async def save_junctions_json():
    async with OpenFileSafely('junctions.json', 'w') as f:
        json.dump({'junctions': map_properties['junctions']}, f)

async def save_markers_json():
    async with OpenFileSafely('markers.json', 'w') as f:
        json.dump({'markers': map_properties['markers']}, f)

async def add_junction():
    print('Adding junction')
    await gps.update(3, led)
    lat, long = gps.latlong()
    map_properties['junctions'].append({'lat': lat, 'long': long})
    await save_junctions_json()
    print('Number of junctions:', len(map_properties['junctions']))

async def delete_junction():
    print('Deleting junction')
    await gps.update(3, led)
    currLatLong = gps.latlong()
    search_range = 50 # meters
    index = -1
    for i, junction in enumerate(map_properties['junctions']):
        junctionLatLong = (junction['lat'], junction['long'])
        dist = gps.dist(currLatLong, junctionLatLong)
        if dist < search_range:
            search_range = dist
            index = i
    if index != -1:
        map_properties['junctions'].pop(index)
        await save_junctions_json()
    print('Number of junctions:', len(map_properties['junctions']))

async def add_marker(text):
    print('Adding marker')
    await gps.update(3, led)
    lat, long = gps.latlong()
    id = str(gps.time()) # ID to link markers to their corresponding images
    new_marker = {'lat': lat, 'long': long, 'text': text.strip(), 'id': id}
    map_properties['markers'].append(new_marker)
    await save_markers_json()
    print('Number of markers:', len(map_properties['markers']))
    return new_marker

async def delete_marker():
    print('Deleting nearest marker')
    await gps.update(3, led)
    currLatLong = gps.latlong()
    search_range = 50 # meters
    index = -1
    for i, marker in enumerate(map_properties['markers']):
        markerLatLong = (marker['lat'], marker['long'])
        dist = gps.dist(currLatLong, markerLatLong)
        if dist < search_range:
            search_range = dist
            index = i
    if index != -1:
        print('Deleting', map_properties['markers'][index])
        deleted_marker = map_properties['markers'].pop(index)
        marker_id = deleted_marker['id']
        print(marker_id)
        if await file_exists('marker_imgs/'+marker_id):
            os.remove('marker_imgs/'+marker_id)
        print('Number of markers:', len(map_properties['markers']))
        await save_markers_json()
    else:
        print('No marker found nearby')

async def view_markers():
    print('Viewing nearby markers')
    change_state(STOPPING)
    await gps.update(3, led)
    currLatLong = gps.latlong()
    markers = map_properties['markers']
    markers.sort(key=lambda marker: gps.dist(currLatLong, (marker['lat'], marker['long'])))
    finished_flag = asyncio.ThreadSafeFlag()
    epd.run_in_thread(epd.view_markers, args=(gps, markers, finished_flag), is_async=True)
    await finished_flag.wait()
    time_to_wait = 20
    for _ in range(time_to_wait*10):
        if epd.key1.value() == 0:
            led.on()
            utime.sleep(0.3)
            led.off()
            utime.sleep(0.7)
            def callback(curr_val):
                print(f'Selected marker = {curr_val}:', markers[curr_val-1]['text'])
            selected_marker = epd.button_select(1, max_val=min(len(markers), 8), on_change_callback=callback)
            epd.run_in_thread(epd.view_marker_img, (markers[selected_marker-1],), is_async=True)
            utime.sleep(0.5)
            break
        utime.sleep(0.1)
    change_state(IDLE)
    asyncio.create_task(display_trails())

async def update_map_properties():
    print('Updating map properties')
    map_properties['bounds'] = None
    tracks = os.listdir('tracks')
    for track in tracks:
        async for lat, long in TrackReader(track):
            # set initial map boundaries
            if map_properties['bounds'] is None:
                map_properties['bounds'] = {}
                map_properties['bounds']['top'] = lat
                map_properties['bounds']['bottom'] = lat
                map_properties['bounds']['left'] = long
                map_properties['bounds']['right'] = long
            
            # NOTE latitude is horizontal, longitude is vertical
            # NOTE latitude increases Northward, longitude increases Eastward
            # update map properties
            if lat > map_properties['bounds']['top']:
                map_properties['bounds']['top'] = lat
            if lat < map_properties['bounds']['bottom']:
                map_properties['bounds']['bottom'] = lat
            if long < map_properties['bounds']['left']:
                map_properties['bounds']['left'] = long
            if long > map_properties['bounds']['right']:
                map_properties['bounds']['right'] = long
        await asyncio.sleep(0)

    # set additional map properties
    map_properties['bounds']['top'] = gps.latToMeters(map_properties['bounds']['top'])
    map_properties['bounds']['bottom'] = gps.latToMeters(map_properties['bounds']['bottom'])
    map_properties['bounds']['left'] = gps.longToMeters(map_properties['bounds']['left'])
    map_properties['bounds']['right'] = gps.longToMeters(map_properties['bounds']['right'])
    map_properties['height'] = (map_properties['bounds']['top']-map_properties['bounds']['bottom'])
    map_properties['width'] = (map_properties['bounds']['right']-map_properties['bounds']['left'])

CURR_TRAIL_WIDTH = 1 # 1-5, in meters
async def change_trail_width():
    # stop recording if necessary
    recording_interrupted = True if CURR_STATE == TRACKING else False
    if recording_interrupted:
        await stop_recording_trail()
        
    # select new trail width
    global CURR_TRAIL_WIDTH
    def callback(curr_val):
        print('Trail width:', curr_val)
    CURR_TRAIL_WIDTH = epd.button_select(CURR_TRAIL_WIDTH, on_change_callback=callback)

    # resume recording if necessary
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
    async with OpenFileSafely('tracks/'+log_filename, 'w') as log:
        log.write('time,latitude,longitude,satellites visible,pdop\n')
    
    # edit tracks.json
    map_properties['tracks'][log_filename] = {'width': CURR_TRAIL_WIDTH}
    await save_tracks_json()
    
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
        async with OpenFileSafely('tracks/'+log_filename, 'a') as log:
            log.write(logEntry)
        lastPointTime = gps.time()
        numPointsTotal += 1
        newPoints += 1

        # write info to epaper
        if gps.time() - epaperDrawTime > epaperDrawInterval:
            epaperDrawTime = gps.time()
            recordingDuration = gps.time()-startTime
            epd.run_in_thread(epd.display_tracking_info,
                              args=(gps.timeFormatted(), recordingDuration, gps.time()-lastPointTime, newPoints, numPointsTotal, CURR_TRAIL_WIDTH),
                              is_async=True)
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
    print('Zoom level:', map_properties['zoom']['levels'][map_properties['zoom']['current']])

async def display_trails():
    tracks = os.listdir('tracks')
    if len(tracks) == 0:
        print("No tracks recorded yet, can't display trails")
        return
    
    finished_flag = asyncio.ThreadSafeFlag()
    while CURR_STATE == IDLE:
        await update_map_properties()
        
        # draw trails
        await gps.update(3)
        print('Displaying recorded trails on e-Paper')
        if CURR_STATE != IDLE:
            return
        epd.run_in_thread(epd.draw_trails, args=(gps, map_properties, finished_flag), is_async=True)

        # wait until finished or state change
        while 1:
            try:
                await asyncio.wait_for_ms(finished_flag.wait(), 200)
                break
            except asyncio.TimeoutError:
                if CURR_STATE != IDLE:
                    return
                continue

### Web app ###

app = pss.App()

async def app_route_home(request: pss.Request):
    body = await pss.get_html_template('home.html')
    body = body.replace('CURR_STATE', CURR_STATE)
    return pss.generate_response(title='TMC Home', body=body)
app.add_route('/', 'GET', app_route_home)

async def app_route_track(request: pss.Request):
    request.parse_form()
    if 'stop' in request.form.keys():
        await stop_recording_trail()
    else:
        asyncio.create_task(start_recording_trail(request.form['filename']))
    return pss.redirect('/')
app.add_route('/track', 'POST', app_route_track)

async def app_route_add_marker(request: pss.Request):
    request.parse_form()
    if 'delete' in request.form.keys():
        await delete_marker()
    else:
        text = request.form['marker-text'].replace('+', ' ').strip()
        await add_marker(text)
    return pss.redirect('/')
app.add_route('/marker', 'POST', app_route_add_marker)

async def app_route_add_image_marker(request: pss.Request):
    # route should only used if pico is started in image receiving mode due to high memory usage
    text = request.headers['Marker-Text']
    new_marker = await add_marker(text)
    print('marker text:', text, '\nmarker id:', new_marker['id'])
    async with OpenFileSafely('marker_imgs/'+new_marker['id'], 'wb') as f:
        f.write(request.file)
    epd.run_in_thread(epd.view_marker_img, args=(new_marker['id'],), is_async=True)
    return pss.generate_response(html=new_marker['id'])
app.add_route('/image_marker', 'POST', app_route_add_image_marker)

async def app_route_view_tracks(request: pss.Request):
    filenames = [file for file in os.listdir('tracks')] + ['tracks.json', 'junctions.json', 'markers.json']
    return pss.generate_response(html=','.join(filenames))
app.add_route('/view_tracks', 'GET', app_route_view_tracks)

async def app_route_download(request: pss.Request):
    filename = request.args["filename"].replace('%20', ' ')
    print('Sending file:', filename)
    fileData = None
    if 'TMC_' in filename: # is a track
        filename = f'tracks/{filename}'
    async with OpenFileSafely(filename, 'r') as f:
        fileData = f.read()
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
    }
    return pss.generate_response(html=fileData, response_headers=headers)
app.add_route('/download', 'GET', app_route_download)

async def app_route_loc(request: pss.Request):
    await gps.update(2, led)
    lat, long = gps.latlong()
    latlong = f'{lat},{long}'
    link = f'https://www.google.com/maps/search/{latlong}'
    atag = f'<a href="{link}" target="_blank">{latlong}</a>'
    return pss.generate_response(body=atag)
app.add_route('/loc', 'GET', app_route_loc)

async def app_route_debug(request: pss.Request):
    await gps.update(3, led)
    debugInfo = gps.getDebugInfo().replace('\n', '<br>')
    body = f'''
        <h2>Debugging info</h2>
        {debugInfo}
    '''
    return pss.generate_response(body=body)
app.add_route('/debug', 'get', app_route_debug)

async def app_route_reset(request: pss.Request):
    soft_reset()
app.add_route('/reset', 'post', app_route_reset)

async def start_web_server():
    server = await asyncio.start_server(app.server_callback, '0.0.0.0', 80, backlog=0)
    print(f'Server running on port 80')
    led.on()
    await server.wait_closed() # serve forever


# main
async def main():
    await flash_led()

    # load in tracks, junctions, and markers data
    async with OpenFileSafely('tracks.json', 'r') as f:
        tracks_json = json.load(f)
        tracks = os.listdir('tracks')
        for track in tracks_json.keys():
            if track not in tracks:
                tracks_json.pop(track)
        map_properties['tracks'] = tracks_json
    await save_tracks_json()

    async with OpenFileSafely('junctions.json', 'r') as f:
        map_properties['junctions'] = json.load(f)['junctions']

    async with OpenFileSafely('markers.json', 'r') as f:
        map_properties['markers'] = json.load(f)['markers']

    # If key1 pressed on startup, initialize gps only and start server immediately.
    # Puts app in marker image receiving mode.
    # Need to do this because if all the other app functionality is loaded into RAM, there's
    # a chance of running out of memory while receiving large images over the web app
    if epd.key1.value() == 0:
        await flash_led(3)
        await gps.initialize()
        await start_web_server()

    # create epaper thread manager and initialize epd
    asyncio.create_task(epd.manage_threads())
    epd.run_in_thread(epd.initialize, args=(
        toggle_trail_recording, # key0_shortpress_func
        change_trail_width, # key0_longpress_func
        add_junction, # key1_shortpress_func
        delete_junction, # key1_longpress_func
        change_zoom_level, # key2_shortpress_func
        view_markers # key2_longpress_func
    ), is_async=False)
    
    # wait while initializing gps
    await gps.initialize()

    # display trails while idling
    asyncio.create_task(display_trails())
    
    # start listening for epd key presses
    asyncio.create_task(epd.key_listener())
    print('e-Paper key listener ready!')
    
    # start web server
    await start_web_server()

# start server
asyncio.run(main())
