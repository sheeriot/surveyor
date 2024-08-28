# from influxdb_client import InfluxDBClient
from influxdb_client_3 import InfluxDBClient3
import pandas as pd

from device.models import InfluxSource

# from time import perf_counter
from icecream import ic


def getGeowanFramesV3(source_id, meas, dev_eui, start, end):
    source = InfluxSource.objects.get(pk=source_id)
    # influx_v3 = source.influx_v3

    influx_org = source.influx_org
    influx_bucket = source.dbname
    influx_token = source.influx_token
    influx_url = f'https://{source.host}'
    start_string = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_string = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    influx_query = f"""
        SELECT _time,gateway,
            rx_time,counter_up,
            bandwidth,spreading_factor,datarate,
            gps_valid,message_type,
            latitude,longitude,duplicate,
            rssi,snr,frequency,
            gw_latitude,gw_longitude,helium,
            tag1,tag2
        FROM { meas }
        WHERE
            dev_eui = '{ dev_eui }'
            AND time >= '{ start_string }'
            AND time <= '{ end_string }'
        """

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

    ic(influx_pdf.info())

    if influx_pdf.empty:
        raise ValueError(F"Dataframe is Empty - check measurement name: {meas}")

    # prune to only GPS_Valid Frames
    influx_pdf['gps_valid'] = influx_pdf['gps_valid'].fillna(False)
    influx_pdf = influx_pdf[influx_pdf['gps_valid']]
    if influx_pdf.empty:
        raise ValueError("No Valid GPS Frames!")

    # now copy for processing
    frames_df = influx_pdf.copy().reset_index(drop=True)
    frames_df = frames_df.dropna(axis=1, how='all')

    # drop rows with no lat/long
    try:
        frames_df = frames_df.dropna(subset=['latitude', 'longitude'])
    except Exception as e:
        raise ValueError(F"Error dropping invalid Lat and Long: ${e}")

    # Convert 'helium' to boolean
    if 'helium' in frames_df.columns:
        frames_df['helium'] = frames_df['helium'].isin([True, 1.0, '1.0', 1])

    if 'latitude' in frames_df.columns:
        frames_df['latitude'] = frames_df['latitude'].round(6)
    if 'longitude' in frames_df.columns:
        frames_df['longitude'] = frames_df['longitude'].round(6)

    if 'rx_time' in frames_df:
        frames_df['time'] = pd.to_datetime(frames_df['rx_time'], unit='s').dt.tz_localize('UTC')
        frames_df = frames_df.drop('rx_time', axis=1)

    if 'device_addr' not in frames_df.columns:
        frames_df['device_addr'] = 'NA'

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
