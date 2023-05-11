import os
import json
from zipfile import ZipFile
import simplekml

DATA_DIR = 'storage/downloads'
IMGS_DIR = 'storage/dcim/Tasker/TMC'
DELETE_AFTER_READ = False

files_to_zip = [os.path.join(DATA_DIR, 'TMC.kml'), os.path.join(IMGS_DIR, 'junction_icon.png'), os.path.join(IMGS_DIR, 'marker_icon.png')]

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
marker_schema: simplekml.Schema = kml.document.newschema()
marker_schema.newsimplefield(name='pdfmaps_photos', type='string', displayname='Photos')
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
    pnt.style.labelstyle.scale = 0
    pnt.style.iconstyle.scale = 1
    pnt.style.iconstyle.icon.href = 'junction_icon.png'
# draw markers
for marker in markers_json['markers']:
    pnt = kml.newpoint(name=f'Marker: {marker["text"]}')
    pnt.coords = [(marker['long'], marker['lat'])]
    pnt.style.labelstyle.scale = 0
    pnt.style.iconstyle.scale = 1
    pnt.style.iconstyle.icon.href = 'marker_icon.png'
    
    # add image if there is one associated with this marker
    img_filename = f"{marker['id']}.jpg"
    img_path = os.path.join(IMGS_DIR, img_filename)
    if os.access(img_path, os.F_OK):
        schema_data = simplekml.SchemaData(marker_schema.id)
        schema_data.newsimpledata('pdfmaps_photos', f'<![CDATA[<img src="{img_filename}" />]]>')
        pnt.extendeddata.datas.append(schema_data)
        files_to_zip.append(img_path)

# Save KML
output = kml.kml()
# print(output)
with open(os.path.join(DATA_DIR, 'TMC.kml'), 'w') as f:
    f.write(output)

# Save KMZ
try:
    os.remove(os.path.join(DATA_DIR, 'TMC.kmz'))
except OSError:
    pass
with ZipFile(os.path.join(DATA_DIR, 'TMC.kmz'), 'w') as zip:
    for file in files_to_zip:
        zip.write(file, os.path.basename(file))
print('\nFinished successfully')