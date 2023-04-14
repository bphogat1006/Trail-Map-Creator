import os
from geopy.distance import distance as geo_distance
import pandas as pd

input_folder = 'pico/tracks'
output_folder = 'pico/tracks_revised'
file_exceptions = [] # files to ignore
look_ahead_exceptions = ['TMC__1680813609.csv'] # files to not apply the look ahead algorithm on
filenames = [file for file in os.listdir(input_folder) if file not in file_exceptions]
LOOK_AHEAD = 20 # * 3 = roughly 1 minute of tracking
MIN_DIST_BTWN_POINTS = 2.5 # meters
OUTLIER_THRESH = 10 # meters

def latlong(track_series):
    lat = track_series['latitude']
    long = track_series['longitude']
    return (lat, long)

track_df: pd.DataFrame = None

# ALGO
compression_vals = []
def revise(file):
    global track_df
    track_df = pd.read_csv(file)
    original_len = len(track_df)
    print('Original Length:', original_len)
    i = 0
    while i < len(track_df):
        global LOOK_AHEAD
        # check for outliers
        if latlong(track_df.iloc[i])[0] == 0 or latlong(track_df.iloc[i])[1] == 0:
            print('---dropping 0 outlier--- at index', i) # should never happen
            track_df.drop(track_df.index[i], axis=0, inplace=True)
            continue
        if 0 < i < len(track_df)-1:
            dist_prev = geo_distance(latlong(track_df.iloc[i]), latlong(track_df.iloc[i-1])).m
            dist_next = geo_distance(latlong(track_df.iloc[i]), latlong(track_df.iloc[i+1])).m
            if dist_prev > OUTLIER_THRESH and dist_next > OUTLIER_THRESH:
                print('---dropping outlier--- index', i, 'dist_prev', dist_prev, 'dist_next', dist_next)
                track_df.drop(track_df.index[i], axis=0, inplace=True)
                continue
            elif dist_prev > OUTLIER_THRESH or dist_next > OUTLIER_THRESH:
                print('---outlier warning--- dist_prev', dist_prev, 'dist_next', dist_next)

        # trim unnecessary data (points that are too close together)
        old_look_ahead = LOOK_AHEAD
        for look_ahead_exception in look_ahead_exceptions: # if file is listed as an exception, only look ahead by 1 point
            if look_ahead_exception in file: # file is a full path. look_ahead_exception is just a file basename
                LOOK_AHEAD = 1
                break
        i2 = min(i+LOOK_AHEAD, len(track_df)-1)
        dupsFound = False
        while i2 > i:
            dist = geo_distance(latlong(track_df.iloc[i]), latlong(track_df.iloc[i2])).m
            if dist < MIN_DIST_BTWN_POINTS:
                dupsFound = True
                break
            else:
                i2 -= 1
        if dupsFound:
            numToRemove = i2-i
            for _ in range(numToRemove):
                track_df.drop(track_df.index[i+1], axis=0, inplace=True)
        else:
            i += 1
        LOOK_AHEAD = old_look_ahead
    revised_len = len(track_df)
    print('Revised Length:', revised_len)
    compression = round((1-revised_len/original_len)*100)
    compression_vals.append(f'{compression}%')
    print(f'Compressed by {compression}%')

# save
def save(file):
    track_df.to_csv(file)

def main():
    for i, filename in enumerate(filenames):
        print(f'\n{i+1}/{len(filenames)}: {filename}')
        revise(os.path.join(input_folder, filename))
        save(os.path.join(output_folder, filename))
    print('\nCompression values:')
    print(compression_vals)
main()