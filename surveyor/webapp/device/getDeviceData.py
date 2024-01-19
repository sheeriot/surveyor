# from time import perf_counter
# from icecream import ic
from influxdb_client import InfluxDBClient
from .models import InfluxSource
import pandas as pd


def getDeviceFrames(source_id, meas, dev_eui, start, end):
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
        |> keep(columns: ["_time","dev_eui","gateway","gateway_eui",
            "rx_time","rcv_time","device_addr","counter_up",
            "duplicate","frame_size","payload_size",
            "bandwidth","datarate","spreading_factor",
            "rssi","snr","frequency",
            "gw_latitude","gw_longitude",
            "message_type","tag1","tag2","pluscode"])
        """

    # start_timer = perf_counter()

    with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
        influx_pdf = client.query_api().query_data_frame(org=influx_org, query=influx_query)
    # stop_timer = perf_counter()
    # query_time = round(stop_timer - start_timer, 1)

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

    if 'rx_time' not in influx_pdf.columns and 'rcv_time' in influx_pdf.columns:
        influx_pdf = influx_pdf.rename(columns={'rcv_time': 'rx_time'})
    if 'gateway' not in influx_pdf.columns and 'gateway_eui' in influx_pdf.columns:
        influx_pdf = influx_pdf.rename(columns={'gateway_eui': 'gateway'})
    if 'device_addr' not in influx_pdf.columns:
        influx_pdf['device_addr'] = 'not'

    # take a copy sorted by time
    frames_df = influx_pdf.copy().reset_index(drop=True).sort_values(by=['rx_time'])

    # work on the time fields
    frames_df['time'] = pd.to_datetime(frames_df['rx_time'], unit='s').dt.tz_localize('UTC')
    # _time and rx_time are UTC
    # frames_df['_time'] = pd.to_datetime(frames_df['_time']).dt.tz_localize('UTC')
    # rename column _time to time

    frames_df = frames_df.drop(columns=['_time', 'rx_time'])

    frames_df['bandwidth'] = frames_df['bandwidth'] / 1000
    frames_df = frames_df.rename(columns={'bandwidth': 'bw_k'})
    frames_df['bw_k'] = frames_df['bw_k'].astype('int')

    frames_df['snr'] = frames_df['snr'].round(1)

    # rename column bandwidth to bw_k
    frames_df = frames_df.astype({
        'counter_up': 'int',
        'bw_k': 'int',
        'spreading_factor': 'int',
        'rssi': 'int',
        'frequency': 'string',
    })

    # change low cardinality (unique volues) columns to category for memory savings
    frames_df = frames_df.astype({
        'frequency': 'category',
        'bw_k': 'category',
        'gateway': 'category',
        'spreading_factor': 'category',
    })
    # if the columns exist, set them first as integers (floats do weird things.)
    if 'frame_size' in frames_df.columns:
        frames_df = frames_df.astype({
            'frame_size': 'int'
        })
    if 'payload_size' in frames_df.columns:
        frames_df = frames_df.astype({
            'payload_size': 'int'
        })
    if 'datarate' in frames_df.columns:
        frames_df = frames_df.astype({
            'datarate': 'int'
        })
        # Then convert to category
        frames_df = frames_df.astype({
            'datarate': 'category'
        })

    frames_df = frames_df.reset_index(drop=True)
    return frames_df
