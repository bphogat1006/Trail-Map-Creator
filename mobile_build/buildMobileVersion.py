import os

try:
    os.remove('viewMapMobile.html')
except:
    pass

def readFile(file):
    with open(os.path.join(os.path.dirname(__file__), file)) as f:
        return f.read()

# my files
viewMapHtml = readFile('../viewMap.html')
drawJs = readFile('../draw.js')
modulesJs = readFile('../modules.js')
# external files
bootstrapCss = readFile('bootstrap.css')
leafletCss = readFile('leaflet.css')
leafletJs = readFile('leaflet.js')
fontawesomeJs = readFile('fontawesome.js')
bootstrapJs = readFile('bootstrap.js')
jqueryJs = readFile('jquery.js')


# build mobile version
mobileBuild = []
for line in viewMapHtml.split('\n'):
    if 'bootstrap.min.css' in line:
        line = f'<style>{bootstrapCss}</style>'
    elif 'leaflet.css' in line:
        line = f'<style>{leafletCss}</style>'
    elif 'leaflet.js' in line:
        line = f'<script>{leafletJs}</script>'
    elif '5d2140906c.js' in line:
        line = f'<script>{fontawesomeJs}</script>'
    elif 'bootstrap.bundle.min.js' in line:
        line = f'<script>{bootstrapJs}</script>'
    elif 'jquery-3.6.0.min.js' in line:
        line = f'<script>{jqueryJs}</script>'
    elif 'id="modulesScript"' in line:
        line = f'<script>{modulesJs}</script>'
    elif 'id="drawScript"' in line:
        line = f'<script>{drawJs}</script>'
    mobileBuild.append(line)

# save to file
with open('viewMapMobile.html', 'w') as f:
    f.write('\n'.join(mobileBuild))