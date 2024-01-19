from celery import shared_task, current_task

import redis
import json

from time import perf_counter
import pandas as pd
# from icecream import ic

from device.models import BucketDevice
from device.locate import pluscode2latlon
from geowan.utils import geoDistance
from .getBucketData import getBucketData


# Add an additional blank line before the decorator
@shared_task
def create_bucketDevicesReport(source_id, meas, start_mark, end_mark, **kwargs):
    task_id = current_task.request.id
    start_time = perf_counter()
    report_status, frames_df = getBucketData(source_id, meas, start_mark, end_mark)
    end_time = perf_counter()
    query_time = round(end_time - start_time, 1)

    if report_status.startswith("Failed"):
        return report_status, {}

    if report_status == "Empty":
        return report_status, {}

    # is gateway location provided (talking to you ran-bridge)
    if 'gw_latitude' in frames_df.columns and 'gw_longitude' in frames_df.columns:
        gw_loc_df = frames_df[['gateway', 'gw_latitude', 'gw_longitude']] \
            .drop_duplicates() \
            .dropna() \
            .reset_index(drop=True)
        gw_loc_df = gw_loc_df.drop_duplicates(subset=['gateway'])
        gw_loc_df = gw_loc_df.rename(columns={'gw_latitude': 'lat', 'gw_longitude': 'long'})
    else:
        # create a blank dataframe for return - No Locations for Gateways!
        gw_loc_df = pd.DataFrame()

    # capture the Tag1/Tag2 for each device

    tag_cols = [col for col in frames_df.columns if col.startswith('tag')]
    # add the dev_eui to the head of tag_cols
    tag_cols.insert(0, 'dev_eui')

    # copy out the tags subset
    device_tags_df = frames_df[tag_cols].copy().drop_duplicates(subset=['dev_eui']).set_index('dev_eui')
    device_uplink_list = frames_df.groupby(["dev_eui", "device_addr", "counter_up"], as_index=False).agg(
        uplink_hits=pd.NamedAgg(column="counter_up", aggfunc="count"),
        uplink_first=pd.NamedAgg(column="_time", aggfunc="min"),
        uplink_last=pd.NamedAgg(column="_time", aggfunc="max"),
        uplink_diff=pd.NamedAgg(column="_time", aggfunc=lambda t: (t.max() - t.min()).microseconds / 1000)
    )
    # create an order for the device_addr (joins)
    ordered_addrs = device_uplink_list.sort_values(["dev_eui", "uplink_first"])["device_addr"].unique()
    device_uplink_list["device_addr"] = pd.Categorical(device_uplink_list["device_addr"], categories=ordered_addrs)
    # add columns - start with Diff
    device_uplink_list['diff'] = (
        device_uplink_list.groupby(['dev_eui', 'device_addr'], observed=True)['counter_up']
        .diff() - 1
    )
    # fill sequence start (na) with 0, set to integer
    device_uplink_list['diff'] = device_uplink_list['diff'].fillna(0).astype(int)

    device_uplinks_df = frames_df.groupby(['dev_eui'], observed=True).agg(
        frames_received=pd.NamedAgg(column='counter_up', aggfunc='count'),
        gateways=pd.NamedAgg(column='gateway', aggfunc=lambda j: j.nunique()),
        join_seqs=pd.NamedAgg(column='device_addr', aggfunc=lambda j: j.nunique()),
        frame_first=pd.NamedAgg(column='_time', aggfunc='min'),
        frame_last=pd.NamedAgg(column='_time', aggfunc='max'),
    )

    # add summary data from uplinks
    device_uplinks2_df = device_uplink_list.groupby(['dev_eui']).agg(
        uplinks_received=pd.NamedAgg(column='counter_up', aggfunc='count'),
        uplinks_missed=pd.NamedAgg(column='diff', aggfunc='sum'),
    )
    device_uplinks_df = device_uplinks_df.join(device_uplinks2_df)

    device_uplinks_df['uplinks_total'] = device_uplinks_df['uplinks_received'] + device_uplinks_df['uplinks_missed']

    device_uplinks_df['uplinks_pdr'] = round(
        device_uplinks_df['uplinks_received'] / device_uplinks_df['uplinks_total'],
        3
    )
    # Add the tags to the device_uplinks_df
    device_uplinks_df = device_uplinks_df.join(device_tags_df)

    if 'pluscode' in frames_df.columns:
        # all candidate pluscodes
        deveui_pluscode_df = frames_df[['dev_eui', 'pluscode']].drop_duplicates().dropna()
        deveui_pluscode_df['pluscode'] = deveui_pluscode_df['pluscode'].str.strip()
        # match this 8+3 pattern only
        pluscode_pattern = r'^[23456789CFGHJMPQRVWX]{8}\+[23456789CFGHJMPQRVWX]{3}$'
        deveui_pluscode_df2 = deveui_pluscode_df[
            deveui_pluscode_df['pluscode'].str.contains(pluscode_pattern, regex=True, na=False)
        ]

        deveui_pluscode_df = deveui_pluscode_df2.drop_duplicates(subset=['dev_eui']).set_index("dev_eui")
        device_uplinks_df = device_uplinks_df.join(deveui_pluscode_df)

    # Device GW DF - Tracking performance by gateway
    device_gw_df = frames_df.groupby(['dev_eui', 'gateway'], observed=True).agg(
        # observed = True,
        frame_count=pd.NamedAgg(column='counter_up', aggfunc='size'),
        rssi_mean=pd.NamedAgg(column='rssi', aggfunc='mean'),
        rssi_std=pd.NamedAgg(column='rssi', aggfunc='std'),
        rssi_min=pd.NamedAgg(column='rssi', aggfunc='min'),
        rssi_max=pd.NamedAgg(column='rssi', aggfunc='max'),
        snr_mean=pd.NamedAgg(column='snr', aggfunc='mean'),
        snr_std=pd.NamedAgg(column='snr', aggfunc='std'),
        snr_min=pd.NamedAgg(column='snr', aggfunc='min'),
        snr_max=pd.NamedAgg(column='snr', aggfunc='max'),
    ).round(1)
    # device_gw_df = device_gw_df[device_gw_df['frame_count'] != 0]
    device_gw_df['rssi_std'] = device_gw_df['rssi_std'].fillna(0)
    device_gw_df['snr_std'] = device_gw_df['snr_std'].fillna(0)
    device_gw_df = device_gw_df.astype({
        'rssi_min': 'int',
        'rssi_max': 'int',
    })
    device_gw_df = device_gw_df.join(device_uplinks_df['uplinks_total'], on='dev_eui')
    # return index columns to DF columns
    device_uplinks_df = device_uplinks_df.reset_index()

    # add the lat/long to the device_gw_df
    # only able to map devices with locations
    if 'pluscode' in device_uplinks_df.columns:
        device_loc_df = device_uplinks_df[['dev_eui', 'pluscode']].copy().dropna()
        device_loc_df['lat'], device_loc_df['long'] = zip(*device_loc_df['pluscode'].apply(pluscode2latlon))
        device_loc_df = device_loc_df.drop(columns=['pluscode']).set_index('dev_eui')
        device_gw_df = device_gw_df.join(device_loc_df[['lat', 'long']], on='dev_eui')
    else:
        device_loc_df = pd.DataFrame(list(BucketDevice.objects.filter(influx_source=source_id).values()))
        if device_loc_df.shape[0] > 0:
            device_loc_df = device_loc_df.drop(columns=['id', 'influx_source_id'])
            device_loc_df['dev_eui'] = device_loc_df['dev_eui'].str.lower()
            device_loc_df = device_loc_df.set_index('dev_eui')
            device_loc_df['lat'] = device_loc_df['lat'].round(6)
            device_loc_df['long'] = device_loc_df['long'].round(6)
            device_gw_df = device_gw_df.join(device_loc_df[['lat', 'long']], on='dev_eui')

    gw_loc_df2 = gw_loc_df.set_index('gateway').add_prefix('gw_')
    device_gw_df = device_gw_df.join(gw_loc_df2, on='gateway')

    got_coords = all(ele in device_gw_df for ele in ['lat', 'long', 'gw_lat', 'gw_long'])

    if got_coords:
        device_gw_df['dist_km'] = device_gw_df.apply(
            lambda row:
                round(geoDistance(row['lat'], row['long'], row['gw_lat'], row['gw_long']) * 1.60934, 2),
            axis=1
        )

    # optimize columns ordering for default presentation
    device_uplinks_cols = [
        'dev_eui',
        'gateways',
        'uplinks_pdr',
        'uplinks_total',
        'uplinks_missed',
        'uplinks_received',
        'frames_received',
        'join_seqs',
        'frame_first',
        'frame_last',
        'tag1',
        'tag2',
        'pluscode'
    ]
    device_uplinks_cols = [col for col in device_uplinks_cols if col in device_uplinks_df.columns]

    device_uplinks_df = device_uplinks_df[device_uplinks_cols]
    # cleanup column order
    device_gw_df = device_gw_df.reset_index()
    device_gw_cols = [
        'dev_eui',
        'gateway',
        'uplinks_total',
        'frame_count',
        'rssi_mean',
        'rssi_std',
        'rssi_min',
        'rssi_max',
        'snr_mean',
        'snr_std',
        'snr_min',
        'snr_max',
        'lat',
        'long',
        'gw_lat',
        'gw_long',
        'dist_km'
    ]
    device_gw_cols = [col for col in device_gw_cols if col in device_gw_df.columns]
    device_gw_df = device_gw_df[device_gw_cols]

    # add the Totals to Redis
    totals_dict = {}

    totals_dict['device_count'] = device_uplinks_df.shape[0]
    totals_dict['gateway_count'] = device_gw_df['gateway'].nunique()
    # a sum of a sum. should match record count
    totals_dict['frames_received'] = int(device_gw_df['frame_count'].sum())
    totals_dict['uplinks_received'] = int(device_uplinks_df['uplinks_received'].sum())
    totals_dict['frame_first'] = device_uplinks_df['frame_first'].min().isoformat()
    totals_dict['frame_last'] = device_uplinks_df['frame_last'].max().isoformat()
    totals_dict['rejoiners'] = len(device_uplinks_df[device_uplinks_df['join_seqs'] > 1])
    totals_dict['rejoin_rate'] = totals_dict['rejoiners'] / totals_dict['device_count'] * 100
    totals_dict['device_uplinks_memsize'] = int(device_uplinks_df.memory_usage(deep=True).sum())
    totals_dict['device_gw_memsize'] = int(device_gw_df.memory_usage(deep=True).sum())
    totals_dict['query_time'] = query_time
    # Connect to Redis
    redis_client = redis.Redis(host='redis', port=6379, db=0)

    redis_client.setex(f'{task_id}:totals_dict', 3600, json.dumps(totals_dict))
    redis_client.setex(f'{task_id}:gw_loc_df', 3600, gw_loc_df.to_json())
    redis_client.setex(f'{task_id}:device_uplinks_df', 3600, device_uplinks_df.to_json())
    redis_client.setex(f'{task_id}:device_gw_df', 3600, device_gw_df.to_json())

    status = "Success"
    return (status, totals_dict)
