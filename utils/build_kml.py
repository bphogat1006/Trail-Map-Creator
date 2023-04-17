import os
import json
from zipfile import ZipFile
import simplekml

DATA_DIR = 'storage/downloads'
DELETE_AFTER_READ = False

# read json files
with open(os.path.join(DATA_DIR, 'tracks.json')) as f:
    tracks_json = json.load(f)
with open(os.path.join(DATA_DIR, 'junctions.json')) as f:
    junctions_json = json.load(f)
with open(os.path.join(DATA_DIR, 'markers.json')) as f:
    markers_json = json.load(f)

# parse CSV files
files = [file for file in os.listdir(DATA_DIR) if file.startswith('TMC_')]
print(files)
tracks = []
for file in files:
    # figure out which columns are which
    latCol = None
    longCol = None
    with open(os.path.join(DATA_DIR, file)) as f:
        lines = f.readlines()
    track = []
    cols = lines[0].split(',')
    for i,col in enumerate(cols):
        if col == 'latitude':
            latCol = i
        elif col == 'longitude':
            longCol = i
    if latCol is None or longCol is None:
        raise Exception('Unable to parse CSV file:', file)

    # parse line by line
    for line in lines[1:]:
        if line.strip() == '':
            break
        parts = line.split(',')
        lat = float(parts[latCol])
        long = float(parts[longCol])
        if lat == 0 or long == 0:
            continue
        track.append((long, lat))

    # append new track
    tracks.append(track)

    if DELETE_AFTER_READ:
        os.remove(os.path.join(DATA_DIR, file))


# Create KML file
kml = simplekml.Kml()
# draw tracks
for i,track in enumerate(tracks):
    ls = kml.newlinestring(name=files[i], coords=track)
    ls.altitudemode = simplekml.AltitudeMode.relativetoground
    trail_width = tracks_json[files[i]]['width'] * 2
    ls.linestyle = simplekml.LineStyle(color=simplekml.Color.rgb(255, 192, 66), width=trail_width)
# draw junctions
for junc in junctions_json['junctions']:
    pnt = kml.newpoint(name=f'Junction: {junc["long"]}, {junc["lat"]}')
    pnt.coords = [(junc['long'], junc['lat'])]
    pnt.style.labelstyle.scale=0
    pnt.style.iconstyle.scale = 1
    pnt.style.iconstyle.icon.href = 'junction_icon.png'
# draw markers
for marker in markers_json['markers']:
    pnt = kml.newpoint(name=f'Marker: {marker["text"]}')
    pnt.coords = [(marker['long'], marker['lat'])]
    pnt.style.labelstyle.scale=0
    pnt.style.iconstyle.scale = 1
    pnt.style.iconstyle.icon.href = 'marker_icon.png'
    pnt.style.balloonstyle.text = marker['text']

# Save KML
output = kml.kml()
print(output)
with open(os.path.join(DATA_DIR, 'TMC.kml'), 'w') as f:
    f.write(output)

# Save KMZ
try:
    os.remove(os.path.join(DATA_DIR, 'TMC.kmz'))
except OSError:
    pass
files_to_zip = ['TMC.kml', 'junction_icon.png', 'marker_icon.png']
with ZipFile(os.path.join(DATA_DIR, 'TMC.kmz'), 'w') as zip:
    for file in files_to_zip:
        zip.write(os.path.join(DATA_DIR, file), file)
print('\nFinished')