import pandas as pd
# from icecream import ic


def device_summ_frames(frames_df):

    device_uplinks_df = frames_df.groupby(["device_addr", "counter_up"],
                                          as_index=False).agg(
        hits=pd.NamedAgg(column="counter_up", aggfunc="count"),
        time=pd.NamedAgg(column="time", aggfunc="min"),
        msec=pd.NamedAgg(column="time",
                         aggfunc=lambda t:
                         (t.max() - t.min()).microseconds/1000),
        rssi=pd.NamedAgg(column="rssi", aggfunc="max"),
        snr=pd.NamedAgg(column="snr", aggfunc="max"),
    )
    device_uplinks_df['msec'] = device_uplinks_df['msec'].astype('int')
    device_uplinks_df['snr'] = device_uplinks_df['snr'].round(1)

    ordered_addrs = device_uplinks_df.sort_values(["time"])["device_addr"].unique()
    device_uplinks_df["device_addr"] = pd.Categorical(device_uplinks_df["device_addr"], categories=ordered_addrs)
    device_uplinks_df = device_uplinks_df.sort_values(["device_addr", "time"])

    # add columns - missed (uplinks), tgap (time between uplinks),
    device_uplinks_df['missed'] = device_uplinks_df.groupby(['device_addr'], observed=True)['counter_up'].diff()-1
    # fill sequence start (na) with 0, set to integer
    device_uplinks_df['missed'] = device_uplinks_df['missed'].fillna(0).astype('int')
    device_uplinks_df['tgap'] = device_uplinks_df['time'].diff().round('s')

    device_uplinks_df = device_uplinks_df.sort_values(["device_addr", "counter_up"])
    device_uplinks_df = device_uplinks_df.set_index(['device_addr', 'counter_up'])

    # now the rejoins. Get the frames in order by dev_addr too!
    frames_df["device_addr"] = pd.Categorical(frames_df["device_addr"], categories=ordered_addrs)
    frames_df = frames_df.sort_values(["device_addr", "counter_up"]).reset_index(drop=True)

    # move common fields from frames_df to device_uplinks_df
    xfer_cols = [
        'dev_eui', 'device_addr', 'counter_up', 'hits',
        'bw_k', 'frequency', 'spreading_factor',
        'datarate', 'frame_size', 'payload_size', 'message_type',
        'tag1', 'tag2', 'pluscode'
    ]
    xfer_cols = [col for col in frames_df.columns if col in xfer_cols]
    xfer_df = pd.DataFrame(frames_df, columns=xfer_cols)
    xfer_df = xfer_df.drop_duplicates(subset=['device_addr', 'counter_up'])
    xfer_df = xfer_df.set_index(['device_addr', 'counter_up'])

    # device_uplinks_df = device_uplinks_df.set_index(['device_addr', 'counter_up'])
    device_uplinks_df = device_uplinks_df.join(xfer_df, how='inner').reset_index()

    # more prep before we pass it to template
    # this re-orders
    uplink_cols = [
        'device_addr', 'counter_up', 'missed',
        'time', 'tgap',
        'hits', 'msec', 'rssi', 'snr',
        'bw_k', 'frequency',
        'spreading_factor', 'datarate', 'frame_size',
        'payload_size', 'message_type'
    ]
    uplink_cols = [col for col in uplink_cols if col in device_uplinks_df.columns]
    device_uplinks_df = device_uplinks_df[uplink_cols]

    # rename columns for narrower table
    device_uplinks_df = device_uplinks_df.rename(
        columns={
            'counter_up': 'count',
            'device_addr': 'addr',
            'spreading_factor': 'sf',
            'datarate': 'dr',
            'frequency': 'freq',
            'frame_size': 'fsize',
            'payload_size': 'psize',
        }
    )

    # # uplink frame is ready, pass it on
    # device_uplinks_df['time'] = device_uplinks_df['time'].dt.tz_convert(local_tz)

    frame_cols = [
        'device_addr', 'counter_up',
        'time', 'gateway', 'duplicate',
        'rssi', 'snr', 'rssi_c',
        'latitude', 'longitude',
        'gw_latitude', 'gw_longitude',
        'distance'
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
            'distance': 'dist',
            'duplicate': 'dup',
        }
    )

    return frames_df, device_uplinks_df
