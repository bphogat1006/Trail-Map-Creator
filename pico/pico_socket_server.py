import socket
import network
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import gc

# set up access point
ssid = "BOBYA_PICO_AP"
pw = '12345678'
ap = network.WLAN(network.AP_IF)
ap.config(essid=ssid, password=pw)
ap.config(pm = 0xa11140) # um what
ap.active(True)
while not ap.isconnected() and ap.status() != 3 and ap.active() == False:
    pass
print(f'Access point {ssid} active')
print(ap.ifconfig())


# set up server

MAX_RECV = 4096
# MAX_SEND = 4096 # unused for now

def normalize_line_endings(s):
    # Convert string containing various line endings like \n, \r or \r\n, to uniform \n.
    return ''.join((line + '\n') for line in s.splitlines())

def get_html_template(template):
    html = None
    with open(template, 'r') as template_file:
        html = template_file.read()
    return html

def generate_response(status_code=200, status_text='', response_headers=dict(), title='TMC', head='', body='', html=None):
    # create response body
    response_body = ''
    if html is None:
        response_body = f'''
            <!doctype html>
            <html lang="en">
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <head>
                    <title>{title}</title>
                    {head}
                </head>
                <body>
                    {body}
                </body>
            </html>'''
    else:
        response_body = html

    # create response headers
    response_headers.update({
        'Content-Type': 'text/html; encoding=utf8',
        'Content-Length': len(response_body),
        'Connection': 'close',
    })
    response_headers_raw = ''.join(f'{k}: {v}\n' for k, v in response_headers.items())

    # Reply as HTTP/1.1 server
    response_headline = f'HTTP/1.0 {status_code} {status_text}\n'

    return response_headline, response_headers_raw, response_body

def redirect(uri):
    headers = {'Location': uri}
    return generate_response(status_code=303, status_text='See Other', response_headers=headers)

class Request:
    def __init__(self, request) -> None:
        requestParts = request.split('\n\n', 1)
        request_head = requestParts[0]
        self.body = '' if len(requestParts)==1 else requestParts[1]

        request_head = request_head.splitlines()
        request_headline = request_head[0]
        if len(request_head) == 1:
            self.headers = dict()
        else:
            self.headers = dict(x.split(': ', 1) for x in request_head[1:])
        self.method, self.route, self.protocol = request_headline.split(' ', 3)

        routeParts = self.route.split('?')
        self.route = routeParts[0]
        if len(routeParts) == 1:
            self.args = dict()
        else:
            queryParams = routeParts[1]
            if queryParams:
                self.args = dict(param.split('=', 1) for param in queryParams.split('&'))
            else:
                self.args = dict()

        # for consistent formatting
        self.method = self.method.lower()
        if self.route[-1] != '/':
            self.route += '/'

class App:
    def __init__(self) -> None:
        self._route_table = {}

    def add_route(self, route, method, gen_response_func):
        # for consistent formatting
        if route[-1] != '/':
            route += '/'
        method = method.lower()
        # add route
        self._route_table[f'{route} {method}'] = gen_response_func

    async def _send_response(self, writer: asyncio.StreamWriter, request: Request):
        # generate & send response
        res = None
        if f'{request.route} {request.method}' not in self._route_table.keys():
            print('404 Not Found')
            res = generate_response(status_code=404, status_text='Not Found', title='404', body='404')
        else:
            res = await self._route_table[f'{request.route} {request.method}'](request)
        response_headline, response_headers_raw, response_body = res
        writer.write(response_headline.encode())
        writer.write(response_headers_raw.encode())
        writer.write('\n'.encode()) # to separate headers from body
        writer.write(response_body.encode())
        await writer.drain()

    async def server_callback(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        gc.collect()
        client_addr = writer.get_extra_info('peername')
        print(f'{client_addr}: New connection request')

        # parse request
        try:
            buf = await asyncio.wait_for_ms(reader.read(MAX_RECV), 500)
            buf = buf.decode()
        except asyncio.TimeoutError:
            print(f'{client_addr}: Connection timed out, closing.')
            writer.close()
            await writer.wait_closed()
            return
        
        request = normalize_line_endings(buf)
        request = Request(request)

        print(f'{client_addr}: {request.method} {request.route}')
        print(f'{client_addr}: Sending response...')
        await self._send_response(writer, request)
        print(f'{client_addr}: Response sent!')

        # close connection
        writer.close()
        await writer.wait_closed()
