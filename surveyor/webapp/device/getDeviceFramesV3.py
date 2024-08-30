from influxdb_client_3 import InfluxDBClient3
import pandas as pd

from .models import InfluxSource
from .deviceFramesFun import tstamp2time

# from time import perf_counter
from icecream import ic


def getDeviceFramesV3(source_id, meas, dev_eui, start, end):
    ic('Get Device Frames V3')
    source = InfluxSource.objects.get(pk=source_id)
    influx_v3 = source.influx_v3

    # add - raise an error if bad
    if not influx_v3:
        # return error = "bad"
        return pd.DataFrame()

    influx_org = source.influx_org
    influx_bucket = source.dbname
    influx_token = source.influx_token
    influx_url = f'https://{source.host}'

    start_string = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    # ic(start_string)
    end_string = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    # ic(end_string)

    influx_query = f"""
        SELECT _time,gateway,
            rx_time,device_addr,counter_up,
            confirmed, ack, lora_mac,
            duplicate,frame_size,payload_size,
            bandwidth,datarate,spreading_factor,
            rssi,snr,frequency,
            gw_latitude,gw_longitude,
            message_type,tag1,tag2,pluscode,helium
        FROM "{ meas }"
        WHERE
            dev_eui = '{ dev_eui }'
            AND time >= '{ start_string }'
            AND time <= '{ end_string }'
        """

    # ic(influx_query)
    # start_timer = perf_counter()

    with InfluxDBClient3(token=influx_token,
                         host=influx_url,
                         org=influx_org,
                         database=influx_bucket) as client:
        reader = client.query(query=influx_query, language="influxql")
    # stop_timer = perf_counter()
    # query_time = round(stop_timer - start_timer, 1)
    # ic(query_time)
    influx_pdf = reader.to_pandas()

    influx_pdf = influx_pdf.dropna(axis=1, how='all')

    if influx_pdf.empty:
        raise ValueError(F"Dataframe is Empty - check measurement name: {meas}")

    if 'rx_time' in influx_pdf.columns:
        # Saved fields are always UTC. Make it timezone aware
        influx_pdf['time'] = pd.to_datetime(influx_pdf['rx_time'], unit='s').dt.tz_localize('UTC')
        influx_pdf = influx_pdf.drop(columns=['rx_time'])

    if 'device_addr' not in influx_pdf.columns:
        influx_pdf['device_addr'] = 'NA'

    # take a copy sorted by time
    # now on 'time'
    frames_df = influx_pdf.copy().reset_index(drop=True).sort_values(by=['time'])

    # Convert 'helium' to boolean
    # frames_df['helium'] = frames_df['helium'].astype('boolean')
    if 'helium' in frames_df.columns:
        frames_df['helium'] = frames_df['helium'].isin([True, 1.0, '1.0', 1])
        if not frames_df['helium'].any():
            frames_df = frames_df.drop(columns=['helium'])

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

    # ic(frames_df.info())
    return frames_df


def getDownlinksV3(source_id, dlmeas, dev_eui, start, end):
    ic('Get Downlinks V3')
    source = InfluxSource.objects.get(pk=source_id)

    influx_org = source.influx_org
    influx_bucket = source.dbname
    influx_token = source.influx_token
    influx_url = f'https://{source.host}'

    start_string = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_string = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    influx_query = f"""
        SELECT *
        FROM "{ dlmeas }"
        WHERE
            dev_eui = '{ dev_eui }'
            AND time >= '{ start_string }'
            AND time <= '{ end_string }'
    """
    # ic(influx_query)

    # start_timer = perf_counter()
    with InfluxDBClient3(token=influx_token,
                         host=influx_url,
                         org=influx_org,
                         database=influx_bucket) as client:
        reader = client.query(query=influx_query, language="influxql")
    # stop_timer = perf_counter()
    # query_time = round(stop_timer - start_timer, 1)
    # ic(query_time)
    influx_pdf = reader.to_pandas()

    if influx_pdf.empty:
        raise ValueError(F"No Downlinks - Measurement: {dlmeas}")

    influx_pdf = influx_pdf.dropna(axis=1, how='all')
    influx_pdf = influx_pdf.drop(columns=['dev_eui'])

    if 'packet_time' in influx_pdf.columns:
        influx_pdf = influx_pdf.drop(columns=['time'])
        influx_pdf = influx_pdf.rename(columns={'packet_time': 'time'})

    influx_pdf['time'] = influx_pdf['time'].apply(lambda t: tstamp2time(str(t)))

    influx_pdf['tx_time'] = influx_pdf['tx_time'].apply(lambda t: tstamp2time(str(t)))

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
    ic(frames_df.info())
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

    ic(frames_df.info())
    return frames_df
