from geopy.distance import distance as geo_distance
import pandas as pd

# load track data
track_df = pd.read_csv('utils/gps_log.csv')
# track_df.set_index('time', inplace=True)

def latlong(track_series):
    lat = track_series['latitude']
    long = track_series['longitude']
    return (lat, long)

# ALGO
LOOK_AHEAD = 60
MIN_DIST_BTWN_POINTS = 3 # meters
OUTLIER_THRESH = 10 # meters
def run():
    global track_df
    i = 0
    while i < len(track_df):
        # print((i)/len(track_df)*100, '%') # progress

        # check for outliers
        if latlong(track_df.iloc[i])[0] == 0:
            print('dropping 0 outlier', i)
            track_df.drop(track_df.index[i], axis=0, inplace=True)
            continue
        if 0 < i < len(track_df)-1:
            d1 = geo_distance(latlong(track_df.iloc[i]), latlong(track_df.iloc[i-1])).m
            d2 = geo_distance(latlong(track_df.iloc[i]), latlong(track_df.iloc[i+1])).m
            if d1 > OUTLIER_THRESH and d2 > OUTLIER_THRESH:
                print('dropping outlier', i, d1, d2)
                track_df.drop(track_df.index[i], axis=0, inplace=True)
                continue
            elif d1 > OUTLIER_THRESH or d2 > OUTLIER_THRESH:
                print('outlier warning: d1', d2, 'd2', d2)

        # trim unnecessary data (points that are too close together)
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
        i += 1

# save
def save(filename):
    print(track_df)
    print('Number of rows:', len(track_df))
    track_df.to_csv(filename)

save('utils/GPS_ORIGINAL.csv')
run()
save('utils/GPS_EDITED.csv')