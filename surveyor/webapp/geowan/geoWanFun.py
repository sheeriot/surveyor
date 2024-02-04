import pandas as pd
# from icecream import ic

from surveyor.utils import computed_rssi
from geopy.distance import geodesic


def geowanSummFrames(frames_df):

    frames_df['distance'] = frames_df.apply(lambda x:
                                            round(geodesic(
                                                    (x['latitude'], x['longitude']),
                                                    (x['gw_latitude'], x['gw_longitude'])
                                            ).km, 3),
                                            axis=1
                                            )

    # computed rssi
    frames_df['rssi_c'] = frames_df.apply(lambda x: computed_rssi(x['rssi'], x['snr']), axis=1)

    uplinks_df = frames_df.groupby(["device_addr", "counter_up"], as_index=False).agg(
        time=pd.NamedAgg(column="time", aggfunc="min"),
        hits=pd.NamedAgg(column="counter_up", aggfunc="count"),
        rssi=pd.NamedAgg(column="rssi", aggfunc="max"),
        rssi_c=pd.NamedAgg(column="rssi_c", aggfunc="max"),
        snr=pd.NamedAgg(column="snr", aggfunc="max"),
    )
    uplinks_df['snr'] = uplinks_df['snr'].round(1)

    ordered_addrs = uplinks_df.sort_values(["time"])["device_addr"].unique()
    uplinks_df["device_addr"] = pd.Categorical(uplinks_df["device_addr"], categories=ordered_addrs)
    uplinks_df = uplinks_df.sort_values(["device_addr", "counter_up"])
    uplinks_df = uplinks_df.set_index(['device_addr', 'counter_up'])
    # move common fields from frames_df to device_uplinks_df
    xfer_cols = [
        'device_addr', 'counter_up',
        'bandwidth', 'frequency', 'spreading_factor',
        'datarate', 'frame_size', 'payload_size',
        'latitude', 'longitude', 'gps_status',
        'message_type', 'tag1', 'tag2', 'pluscode'
    ]

    xfer_cols = [col for col in xfer_cols if col in frames_df.columns]
    xfer_df = pd.DataFrame(frames_df, columns=xfer_cols)
    xfer_df = xfer_df.drop_duplicates(subset=['device_addr', 'counter_up'])
    xfer_df = xfer_df.set_index(['device_addr', 'counter_up'])
    uplinks_df = uplinks_df.join(xfer_df, how='inner').reset_index()

    # =================
    # cleanup uplink columns order
    uplink_cols = [
        'device_addr', 'counter_up', 'time', 'hits',
        'rssi', 'snr', 'rssi_c',
        'latitude', 'longitude',
        'frequency', 'bandwidth',
        'spreading_factor', 'datarate', 'gps_status',
        'message_type', 'tag1', 'tag2'
    ]
    uplink_cols = [col for col in uplink_cols if col in uplinks_df.columns]
    uplinks_df = uplinks_df[uplink_cols]

    uplinks_df['bandwidth'] = uplinks_df['bandwidth'].astype('int') / 1000
    uplinks_df['bandwidth'] = uplinks_df['bandwidth'].astype('int')
    uplinks_df = uplinks_df.rename(columns={'bandwidth': 'bw_k'})

    # rename some column name for narrower display
    uplinks_df = uplinks_df.rename(
        columns={
            'device_addr': 'addr',
            'counter_up': 'count',
            'spreading_factor': 'sf',
            'datarate': 'dr',
            'frequency': 'freq',
            'latitude': 'lat',
            'longitude': 'long',
            'gw_latitude': 'gw_lat',
            'gw_longitude': 'gw_long',
            'distance': 'dist',
            'message_type': 'message',
            'gps_status': 'gps',
        }
    )

    # cleanup the frames_df for presentation
    frame_cols = [
        'device_addr', 'counter_up',
        'time', 'gateway', 'duplicate',
        'rssi', 'snr', 'rssi_c',
        'latitude', 'longitude',
        'gw_latitude', 'gw_longitude',
        'distance',
    ]
    frame_cols = [col for col in frame_cols if col in frames_df.columns]
    # prune the frames
    frames_df = frames_df[frame_cols]
    frames_df = frames_df.rename(
        columns={
            'device_addr': 'addr',
            'counter_up': 'count',
            'gw_latitude': 'gw_lat',
            'gw_longitude': 'gw_long',
            'latitude': 'lat',
            'longitude': 'long',
            'distance': 'dist',
            'duplicate': 'dup',
        }
    )

    return frames_df, uplinks_df
