import os
from utime import sleep
from machine import UART, Pin, reset
from _thread import start_new_thread
from onboard_led import led, flash_led
from epaper import EPD_2in7
from gpsUtils import GPS
import picoSocketServer as pss

flash_led()

# init GPS
gps = GPS(UART(0, tx=Pin(0), rx=Pin(1), baudrate=9600), debug=False)
gps.init()
gps.update(3)
print('GPS ready')

# init e-Paper
#epd = EPD_2in7()
#epd.image4Gray.fill(0xff)
#epd.image4Gray.text('Ready for something!', 5, 5, epd.black)
#epd.EPD_2IN7_4Gray_Display(epd.buffer_4Gray)
key0 = Pin(15, Pin.IN, Pin.PULL_UP)
key1 = Pin(17, Pin.IN, Pin.PULL_UP)
key2 = Pin(2,  Pin.IN, Pin.PULL_UP)
print('e-Paper ready')

#################################################

# debugging
while 0:
    gps.update(1, led)
    print(gps.getDebugInfo())
    sleep(1.1)

# state vars
IDLE = 'IDLE'
TRACKING = 'TRACKING'
STOPPING = 'STOPPING'

# current state
CURR_STATE = IDLE

def changeState(newState):
    global CURR_STATE
    CURR_STATE = newState
    print('State change:', newState)

# log cooords to file
def startLoggingGPS(log_description):
    log_description = log_description.strip().replace('+', '-')
    log_filename = f'logs/TMC_{log_description}_{gps.getTime()}.csv'
    print('opening new log:', log_filename)
    gps.update(3) # let app return html page
    with open(log_filename, 'w') as log:
        log.write('time,latitude,longitude,satellites visible,pdop\n')
    while 1:
        # update and log
        gps.update(1)
        lat, long = gps.latlong()
        satellitesVisible = len(gps.reader.satellites_visible())
        pdop = gps.reader.pdop
        logEntry = f'{gps.getTime()},{lat},{long},{satellitesVisible},{pdop}\n'
        print(logEntry)
        with open(log_filename, 'a') as log:
            log.write(logEntry)

        # delay
        if CURR_STATE == STOPPING:
            changeState(IDLE)
            break
        sleep(2)

# init web app
app = pss.App()

def home(request: pss.Request):
    body = pss.get_html_template('home.html')
    body = body.replace('CURR_STATE', CURR_STATE)
    return pss.generate_response(title='TMC Home', body=body)
app.add_route('/', 'GET', home)

def track(request: pss.Request):
    paramDict = dict((param.split('=')[0], param.split('=')[1]) for param in request.body.split('&'))
    print(paramDict)
    if 'stop' in paramDict.keys():
        changeState(STOPPING)
        while CURR_STATE != IDLE:
            pass
    else:
        changeState(TRACKING)
        start_new_thread(startLoggingGPS, (paramDict['filename'],))
    return pss.redirect('/')
app.add_route('/track', 'post', track)

def view_tracks(request: pss.Request):
    downloadPage = pss.get_html_template('download.html')
    filenames = [file for file in os.listdir('logs')]
    downloadPage = downloadPage.replace('FILENAMES', ','.join(filenames))
    return pss.generate_response(body=downloadPage)
app.add_route('/view_tracks', 'GET', view_tracks)

def download(request: pss.Request):
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

def loc(request: pss.Request):
    gps.update(2, led)
    lat, long = gps.latlong()
    latlong = f'{lat},{long}'
    link = f'https://www.google.com/maps/search/{latlong}'
    atag = f'<a href="{link}" target="_blank">{latlong}</a>'
    return pss.generate_response(body=atag)
app.add_route('/loc', 'GET', loc)

def debug(request: pss.Request):
    gps.update(3, led)
    debugInfo = gps.getDebugInfo().replace('\n', '<br>')
    body = f'''
        <h2>Debugging info</h2>
        <p>{debugInfo}</p>
    '''
    return pss.generate_response(body=body)
app.add_route('/debug', 'get', debug)

# ready
led.on()
app.run()
