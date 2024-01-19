from celery import shared_task
# from influxdb_client import InfluxDBClient

# import dateutil.parser
# import dateutil.tz
# from time import perf_counter
import pandas as pd
# from icecream import ic

from .getBucketData import getBucketData


@shared_task
def bucketDevicesReport(source_id, meas, start_mark, end_mark, **kwargs):

    report_status, frames_df = getBucketData(source_id, meas, start_mark, end_mark)

    if report_status.startswith("Failed") or "Empty" in report_status:

        return report_status, frames_df.to_json(), pd.DataFrame().to_json(), pd.DataFrame().to_json()

    # is gateway location provided (talking to you ran-bridge)
    if 'gw_latitude' in frames_df.columns and 'gw_longitude' in frames_df.columns:
        gw_loc_df = frames_df[['gateway', 'gw_latitude', 'gw_longitude']] \
            .drop_duplicates() \
            .dropna() \
            .reset_index(drop=True)
        gw_loc_df = gw_loc_df.drop_duplicates(subset=['gateway'])
        gw_loc_df = gw_loc_df.rename(columns={'gw_latitude': 'lat', 'gw_longitude': 'long'})
    else:
        gw_loc_df = pd.DataFrame()

    # capture the Tag1/Tag2 for each device
    # pandas drop duplicates keeps the first row, so we can use this to get the first tag

    tag_cols = [col for col in frames_df.columns if col.startswith('tag')]
    # add the dev_eui to the tag_cols
    tag_cols.insert(0, 'dev_eui')
    device_tags_df = frames_df[tag_cols].drop_duplicates(subset=['dev_eui']).set_index('dev_eui')

    device_uplink_list = frames_df.groupby(["dev_eui", "device_addr", "counter_up"], as_index=False).agg(
        uplink_hits=pd.NamedAgg(column="counter_up", aggfunc="count"),
        uplink_first=pd.NamedAgg(column="_time", aggfunc="min"),
        uplink_last=pd.NamedAgg(column="_time", aggfunc="max"),
        uplink_diff=pd.NamedAgg(column="_time", aggfunc=lambda t: (t.max() - t.min()).microseconds/1000)
    )
    # create an order for the device_addr (joins)
    ordered_addrs = device_uplink_list.sort_values(["dev_eui", "uplink_first"])["device_addr"].unique()
    device_uplink_list["device_addr"] = pd.Categorical(device_uplink_list["device_addr"], categories=ordered_addrs)
    # add columns - start with Diff
    device_uplink_list['diff'] = device_uplink_list.groupby(['dev_eui', 'device_addr'])['counter_up'].diff()-1
    # fill sequence start (na) with 0, set to integer
    device_uplink_list['diff'] = device_uplink_list['diff'].fillna(0).astype('int')

    device_summ_df = frames_df.groupby('dev_eui').agg(
        frames_received=pd.NamedAgg(column='counter_up', aggfunc='count'),
        join_seqs=pd.NamedAgg(column='device_addr', aggfunc=lambda j: j.nunique()),
        frame_first=pd.NamedAgg(column='_time', aggfunc='min'),
        frame_last=pd.NamedAgg(column='_time', aggfunc='max'),
    )

    # add summary data from uplinks
    device_summ2_df = device_uplink_list.groupby(['dev_eui']).agg(
        uplinks_received=pd.NamedAgg(column='counter_up', aggfunc='count'),
        uplinks_missed=pd.NamedAgg(column='diff', aggfunc='sum'),
    )
    device_summ_df = device_summ_df.join(device_summ2_df)

    device_summ_df['uplinks_total'] = device_summ_df['uplinks_received'] + device_summ_df['uplinks_missed']

    device_summ_df['uplinks_pdr'] = round(device_summ_df['uplinks_received'] / (device_summ_df['uplinks_total']), 3)
    # Add the tags to the device_summ_df
    device_summ_df = device_summ_df.join(device_tags_df)

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
        device_summ_df = device_summ_df.join(deveui_pluscode_df)

    # Device GW DF - Tracking performance by gateway
    device_gw_df = frames_df.groupby(['dev_eui', 'gateway']).agg(
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
    device_gw_df = device_gw_df[device_gw_df['frame_count'] != 0]
    device_gw_df['rssi_std'] = device_gw_df['rssi_std'].fillna(0)
    device_gw_df['snr_std'] = device_gw_df['snr_std'].fillna(0)
    device_gw_df = device_gw_df.astype({
        'rssi_min': 'int',
        'rssi_max': 'int',
    })
    device_gw_df = device_gw_df.join(device_summ_df['uplinks_total'], on='dev_eui')
    device_gw_df = device_gw_df.reset_index()
    device_summ_df = device_summ_df.reset_index()

    status = "Success"
    return (status, gw_loc_df.to_json(), device_summ_df.to_json(), device_gw_df.to_json())
