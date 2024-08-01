from time import perf_counter
from icecream import ic
from influxdb_client import InfluxDBClient
from .models import InfluxSource
import pandas as pd
from .deviceFramesFun import tstamp2time


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
            "confirmed", "ack", "lora_mac",
            "duplicate","frame_size","payload_size",
            "bandwidth","datarate","spreading_factor",
            "rssi","snr","frequency",
            "gw_latitude","gw_longitude",
            "message_type","tag1","tag2","pluscode", "helium"])
        """

    start_timer = perf_counter()

    with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
        influx_pdf = client.query_api().query_data_frame(org=influx_org, query=influx_query)
    stop_timer = perf_counter()
    query_time = round(stop_timer - start_timer, 1)
    # ic(query_time)
    # this normalizes the list into a DF by adding missing columns and appending
    if type(influx_pdf) is list:
        append_flag = False
        df_list = influx_pdf
        columns_set = set([col for df in df_list for col in df.columns])

        frames_df = pd.DataFrame()
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

    # use rx_time (or  rcv_time) if available - gateway time?
    if 'rx_time' not in influx_pdf.columns and 'rcv_time' in influx_pdf.columns:
        influx_pdf = influx_pdf.rename(columns={'rcv_time': 'rx_time'})
    if 'rx_time' in influx_pdf.columns:
        # Saved fields are always UTC. Make it timezone aware
        influx_pdf['time'] = pd.to_datetime(influx_pdf['rx_time'], unit='s').dt.tz_localize('UTC')
        influx_pdf = influx_pdf.drop(columns=['rx_time'])
    else:
        # use DB time
        influx_pdf['time'] = influx_pdf['_time']

    influx_pdf = influx_pdf.drop(columns=['_time'])

    # might be named gateway_eui
    if 'gateway' not in influx_pdf.columns and 'gateway_eui' in influx_pdf.columns:
        influx_pdf = influx_pdf.rename(columns={'gateway_eui': 'gateway'})
    if 'device_addr' not in influx_pdf.columns:
        influx_pdf['device_addr'] = 'not'

    # take a copy sorted by time
    # now on 'time'
    frames_df = influx_pdf.copy().reset_index(drop=True).sort_values(by=['time'])

    # Convert 'helium' to boolean
    # frames_df['helium'] = frames_df['helium'].astype('boolean')
    if 'helium' in frames_df.columns:
        frames_df['helium'] = frames_df['helium'].isin([True, 1.0, '1.0', 1])

    # drop the zeros in bandwidth
    if 'bandwidth' in frames_df.columns:
        frames_df['bandwidth'] = frames_df['bandwidth'] / 1000
        frames_df = frames_df.rename(columns={'bandwidth': 'bw_k'})
        frames_df['bw_k'] = frames_df['bw_k'].astype('int')

    # drop stupid floating point crud (digits)
    frames_df['snr'] = frames_df['snr'].round(1)

    frames_df = frames_df.astype({
        'counter_up': 'int',
        'spreading_factor': 'int',
        'rssi': 'int',
        'frequency': 'string',
    })

    # change low cardinality (unique volues) columns to category for memory savings
    frames_df = frames_df.astype({
        'frequency': 'category',
        'gateway': 'category',
        # 'spreading_factor': 'category', # keep it as integer for calculations
    })

    if 'bw_k' in frames_df.columns:
        frames_df = frames_df.astype({
            'bw_k': 'category',
        })

    # Cast frame_size or payload_size columns to Int64 type, which happily works with NA values
    if 'frame_size' in frames_df.columns:
        frames_df = frames_df.astype({
            'frame_size': 'Int64'
        })
    if 'payload_size' in frames_df.columns:
        frames_df = frames_df.astype({
            'payload_size': 'Int64'
        })
    # Change the DataRate to Integer
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


def getDownlinks(source_id, dlmeas, dev_eui, start, end):
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
        |> filter(fn:(r) => r._measurement == "{dlmeas}" and r.dev_eui == "{dev_eui}")
        |> drop(fn: (column) => column =~ /^_(start|stop|measurement)/)
        |> pivot(rowKey:["dev_eui","_time"], columnKey: ["_field"], valueColumn: "_value")
        """
    # |> keep(columns: ["_time","dev_eui","gateway","gateway_eui",
    #     "rx_time","rcv_time","device_addr","counter_up",
    #     "duplicate","frame_size","payload_size",
    #     "bandwidth","datarate","spreading_factor",
    #     "rssi","snr","frequency",
    #     "gw_latitude","gw_longitude",
    #     "message_type","tag1","tag2","pluscode", "helium"])

    start_timer = perf_counter()

    with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
        influx_pdf = client.query_api().query_data_frame(org=influx_org, query=influx_query)
    stop_timer = perf_counter()
    query_time = round(stop_timer - start_timer, 1)
    # ic(query_time)

    # this normalizes a list of DF into a single DF by adding missing columns and appending
    if type(influx_pdf) is list:
        append_flag = False
        df_list = influx_pdf
        columns_set = set([col for df in df_list for col in df.columns])

        frames_df = pd.DataFrame()
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
        raise ValueError(F"No Downlinks - Measurement: {dlmeas}")

    # try/catch error
    try:
        influx_pdf = influx_pdf.drop(columns=['result', 'table'])
    except influx_pdf.DoesNotExist:
        raise ValueError(F"No Result/Table: {dlmeas}")

    influx_pdf = influx_pdf.rename(columns={'packet_time': 'time'})
    influx_pdf['time'] = influx_pdf['time'].apply(lambda t: tstamp2time(str(t)))
    influx_pdf['tx_time'] = influx_pdf['tx_time'].apply(lambda t: tstamp2time(str(t)))

    influx_pdf = influx_pdf.drop(columns=['_time', 'dev_eui'])

    # take a copy sorted by time
    # now on 'time'
    frames_df = influx_pdf.copy().reset_index(drop=True).sort_values(by=['time'])

    frames_df = frames_df.astype({
        'counter_down': 'int',
        'spreading_factor': 'int',
        'frequency': 'string',
    })

    # change low cardinality (unique volues) columns to category for memory savings
    frames_df = frames_df.astype({
        'frequency': 'category',
        'gateway': 'category',
    })

    # Cast frame_size or payload_size columns to Int64 type, which happily works with NA values
    if 'frame_size' in frames_df.columns:
        frames_df = frames_df.astype({
            'frame_size': 'Int64'
        })

    if 'payload_size' in frames_df.columns:
        frames_df = frames_df.astype({
            'payload_size': 'Int64'
        })

    # Change the DataRate to Integers, then a category
    if 'datarate' in frames_df.columns:
        frames_df = frames_df.astype({
            'datarate': 'int'
        })
        # Then convert to category
        frames_df = frames_df.astype({
            'datarate': 'category'
        })
    if 'port' in frames_df.columns:
        frames_df = frames_df.astype({
            'port': 'Int64'
        })
        # Then convert to category
        frames_df = frames_df.astype({
            'port': 'category'
        })
    # ic(frames_df.info())
    # this re-orders, and filters column names
    downlink_cols = [
        'time', 'tx_time', 'counter_down', 'gateway', 'confirmed', 'ack',
        'frequency', 'datarate', 'spreading_factor',
        'frame_size', 'payload', 'port', 'lora_mac'
    ]
    downlink_cols = [col for col in downlink_cols if col in frames_df.columns]
    frames_df = frames_df[downlink_cols]

    # rename columns for narrower table
    frames_df = frames_df.rename(
        columns={
            'counter_down': 'count',
            'confirmed': 'conf_req',
            'ack': 'conf_ack',
            'device_addr': 'addr',
            'datarate': 'dr',
            'frequency': 'freq',
            'spreading_factor': 'sf',
            'frame_size': 'fsize'
        }
    )

    frames_df = frames_df.reset_index(drop=True)

    return frames_df
