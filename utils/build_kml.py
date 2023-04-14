import os
import simplekml

TRACKS_PATH = 'storage/downloads'
DELETE_AFTER_READ = False

files = [file for file in os.listdir(TRACKS_PATH) if file.startswith('TMC_')]
print(files)

# parse CSV files
tracks = []
for file in files:
    # figure out which columns are which
    latCol = None
    longCol = None
    with open(os.path.join(TRACKS_PATH, file)) as f:
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
        os.remove(os.path.join(TRACKS_PATH, file))


# Create KML file
kml = simplekml.Kml()
for i,track in enumerate(tracks):
    ls = kml.newlinestring(name=files[i], coords=track)
    ls.altitudemode = simplekml.AltitudeMode.relativetoground
    ls.linestyle = simplekml.LineStyle(color=simplekml.Color.black, width=3)

# Save
output = kml.kml()
print(output)
with open(os.path.join(TRACKS_PATH, 'generated.kml'), 'w') as f:
    f.write(output)

