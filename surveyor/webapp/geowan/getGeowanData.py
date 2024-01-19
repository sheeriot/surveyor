# from time import perf_counter
from icecream import ic
from influxdb_client import InfluxDBClient
from device.models import InfluxSource
import pandas as pd


def getGeowanFrames(source_id, meas, dev_eui, start, end):
    source = InfluxSource.objects.get(pk=source_id)

    influx_org = source.influx_org
    influx_bucket = source.dbname
    influx_token = source.influx_token
    influx_url = f'https://{source.host}'
    start_string = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_string = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    influx_query = f"""
        from(bucket: "{influx_bucket}")
        |> range(start: {start_string}, stop: {end_string})
        |> filter(fn:(r) => r._measurement == "{meas}" and r.dev_eui == "{dev_eui}")
        |> drop(fn: (column) => column =~ /^_(start|stop|measurement)/)
        |> pivot(rowKey:["dev_eui","_time"], columnKey: ["_field"], valueColumn: "_value")
        |> keep(columns: ["_time","dev_eui","device_addr",
            "gateway","gateway_eui",
            "rx_time","rcv_time","f_count","counter_up",
            "bandwidth","spreading_factor","datarate",
            "gps_valid","gps_status","message_type",
            "latitude","longitude","duplicate",
            "rssi","snr","frequency",
            "gw_latitude","gw_longitude",
            "tag1","tag2"])
    """

    # start_timer = perf_counter()

    with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
        influx_pdf = client.query_api().query_data_frame(org=influx_org, query=influx_query)
    # stop_timer = perf_counter()
    # query_time = round(stop_timer - start_timer,1)

    # if influx_pdf.status_code == 401:
    #     raise ValueError("401: InfluxDB Authentication Error")

    # this normalizes the list into a DF by adding missing columns and appending
    if type(influx_pdf) is list:
        append_flag = False
        df_list = influx_pdf
        columns_set = set([col for df in df_list for col in df.columns])
        frames_df = pd.empty()
        for df in df_list:
            missing_cols = columns_set - set(df.columns)
            df = df.reindex(columns=df.columns.tolist() + list(missing_cols))
            if append_flag:
                frames_df = pd.concat([frames_df, df], axis=0)
            else:
                frames_df = df
                append_flag = True
        influx_pdf = frames_df.reset_index(drop=True)

    if influx_pdf.empty:
        raise ValueError(F"Dataframe is Empty - check measurement name: {meas}")

    # try/catch error
    try:
        influx_pdf = influx_pdf.drop(columns=['result', 'table'])
    except influx_pdf.DoesNotExist:
        raise ValueError(F"No Result/Table: {meas}")

    # prune to only GPS_Valid Frames
    influx_pdf = influx_pdf[influx_pdf['gps_valid']]
    if influx_pdf.empty:
        raise ValueError("No Valid GPS Frames!")

    # now copy for processing
    frames_df = influx_pdf.copy().reset_index(drop=True)

    # drop rows with no lat/long
    try:
        frames_df = frames_df.dropna(subset=['latitude', 'longitude'])
    except Exception as e:
        ic(f"An unexpected error occurred: {e}")
        raise ValueError(F"Error dropping invalid Lat and Long: ${e}")

    if 'latitude' in frames_df.columns:
        frames_df['latitude'] = frames_df['latitude'].round(6)
    if 'longitude' in frames_df.columns:
        frames_df['longitude'] = frames_df['longitude'].round(6)

    if 'rcv_time' in frames_df.columns:
        if 'rx_time' not in frames_df.columns:
            frames_df = frames_df.rename(columns={'rcv_time': 'rx_time'})
        else:
            frames_df = frames_df.drop(columns=['rcv_time'])

    if 'rx_time' in frames_df:
        frames_df['time'] = pd.to_datetime(frames_df['rx_time'], unit='s').dt.tz_localize('UTC')
        frames_df = frames_df.drop('_time', axis=1)
    else:
        raise ValueError(F"No rx_time: {meas}")

    if 'gateway_eui' in frames_df.columns:
        if 'gateway' not in frames_df.columns:
            frames_df = frames_df.rename(columns={'gateway_eui': 'gateway'})
        else:
            frames_df = frames_df.drop(columns=['gateway_eui'])

    if 'device_addr' not in frames_df.columns:
        frames_df['device_addr'] = '0000'

    if 'snr' in frames_df.columns:
        frames_df['snr'] = frames_df['snr'].round(1)

    frames_df = frames_df.astype({
        'counter_up': 'int',
        'bandwidth': 'int',
        'spreading_factor': 'int',
        'rssi': 'int',
        'frequency': 'string',
    })

    # change low cardinality (unique volues) columns to category for memory savings
    frames_df = frames_df.astype({
        'frequency': 'category',
        'bandwidth': 'category',
        'gateway': 'category',
        'spreading_factor': 'category',
    })
    # if the columns exist, set them first as integers (floats do weird things.)
    if 'gps_status' in frames_df.columns:
        frames_df = frames_df.astype({
            'gps_status': 'int'
        })
        # Then convert to category
        frames_df = frames_df.astype({
            'gps_status': 'category'
        })
    if 'datarate' in frames_df.columns:
        frames_df = frames_df.astype({
            'datarate': 'int'
        })
        # Then convert to category
        frames_df = frames_df.astype({
            'datarate': 'category'
        })

    frames_df = frames_df.sort_values(by=['time']).reset_index(drop=True)
    return frames_df
