# from django.conf import settings
import pandas as pd
import dateutil.parser
import dateutil.tz
from influxdb_client_3 import InfluxDBClient3

from device.models import InfluxSource, BucketDevice
from device.deviceFramesFun import tstamp2time

from icecream import ic
# from time import perf_counter


def getBucketDataV3(source_id, meas, start_mark, end_mark, report_group):
    source = InfluxSource.objects.get(pk=source_id)

    influx_url = f"https://{source.host}"

    zulu_tz = dateutil.tz.gettz('UTC')
    start_zulu = dateutil.parser.parse(start_mark).replace(tzinfo=zulu_tz)
    start_string = start_zulu.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_zulu = dateutil.parser.parse(end_mark).replace(tzinfo=zulu_tz)
    end_string = end_zulu.strftime("%Y-%m-%dT%H:%M:%SZ")

    influx_org = source.influx_org
    influx_bucket = source.dbname
    influx_token = source.influx_token
    influx_url = f'https://{source.host}'

    if report_group == 'None':
        influx_query = f"""
            SELECT time, rx_time, counter_up,  dev_eui, device_addr, gateway, duplicate, frame_size,
            frequency, bandwidth, spreading_factor, datarate, rssi, snr,
            gw_latitude, gw_longitude
            FROM "{ meas }"
            WHERE
                time >= '{ start_string }'
                AND time <= '{ end_string }'
            """

    else:
        bucket_devices = BucketDevice.objects.filter(influx_source=source, report_group=report_group)
        dev_eui_list = [device.dev_eui for device in bucket_devices]
        dev_eui_csv = ','.join([f"'{ dev_eui }'" for dev_eui in dev_eui_list])

        influx_query = f"""
            SELECT time, rx_time, counter_up,  dev_eui, device_addr, gateway, duplicate, frame_size,
                frequency, bandwidth, spreading_factor, datarate, rssi, snr,
                gw_latitude, gw_longitude
            FROM "{ meas }"
            WHERE
                dev_eui IN ({ dev_eui_csv })
                AND time >= '{ start_string }'
                AND time <= '{ end_string }'
            """
        # influx_query = """
        #     SELECT time, rx_time, counter_up,  dev_eui, device_addr, gateway, duplicate, frame_size,
        #         frequency, bandwidth, spreading_factor, datarate, rssi, snr, gw_latitude, gw_longitude
        #     FROM "jundiai"
        #     WHERE
        #         dev_eui IN ('00ee01000001effa','00ee01000001c037','00ee0100000210ff')
        #         AND time >= '2024-08-29T04:00:00Z'
        #         AND time <= '2024-08-30T15:02:00Z'
        # """

    # start_timer = perf_counter()
    with InfluxDBClient3(token=influx_token,
                         host=influx_url,
                         org=influx_org,
                         database=influx_bucket) as client:
        try:
            reader = client.query(query=influx_query, language="sql")
            influx_pdf = reader.to_pandas()
        except Exception as e:
            report_status = F'Failed: {e}'
            return report_status, pd.DataFrame()

    # stop_timer = perf_counter()
    # query_time = round(stop_timer - start_timer, 1)

    if influx_pdf.empty:
        raise ValueError(F"Dataframe is Empty - check measurement name: {meas}")

    if influx_pdf.shape[0] == 0:
        report_status = "Empty"
        return report_status, influx_pdf

    influx_pdf = influx_pdf.dropna(axis=1, how='all')

    # fix a few inconsistent column names
    if 'device_addr' not in influx_pdf.columns:
        influx_pdf['device_addr'] = 'NA'

    # make a copy for return
    pdf = influx_pdf.copy().sort_values(by=['dev_eui', 'rx_time']).reset_index(drop=True)
    if 'rx_time' in pdf.columns:
        pdf = pdf.astype({'rx_time': 'string'})

    # Setup Data Types in dataframe
    pdf = pdf.astype({
        'counter_up': 'Int64',
        'spreading_factor': 'Int64',
        'rssi': 'Int64',
        'frequency': 'string',
    })
    if 'bandwidth' in pdf.columns:
        pdf = pdf.astype({'bandwidth': 'Int64'})
        pdf = pdf.astype({'bandwidth': 'category'})
    if 'datarate' in pdf.columns:
        pdf = pdf.astype({'datarate': 'Int64'})
    if 'frame_size' in pdf.columns:
        pdf = pdf.astype({'frame_size': 'Int64'})
    if 'payload_size' in pdf.columns:
        pdf = pdf.astype({'payload_size': 'Int64'})
    #
    if 'tag1' in pdf.columns:
        pdf = pdf.astype({'tag1': 'string'})
    if 'tag2' in pdf.columns:
        pdf = pdf.astype({'tag2': 'string'})

    # change low cardinality to category for memory savings
    pdf = pdf.astype({
        'frequency': 'category',
        'gateway': 'category',
        })
    if 'datarate' in pdf.columns:
        pdf = pdf.astype({'datarate': 'category'})

    query_results = "Success"
    return query_results, pdf


def getBucketDownlinksV3(source_id, dlmeas, start_mark, end_mark, report_group):

    zulu_tz = dateutil.tz.gettz('UTC')
    start_zulu = dateutil.parser.parse(start_mark).replace(tzinfo=zulu_tz)
    start_string = start_zulu.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_zulu = dateutil.parser.parse(end_mark).replace(tzinfo=zulu_tz)
    end_string = end_zulu.strftime("%Y-%m-%dT%H:%M:%SZ")

    source = InfluxSource.objects.get(pk=source_id)
    influx_org = source.influx_org
    influx_bucket = source.dbname
    influx_token = source.influx_token
    influx_url = f'https://{source.host}'

    if report_group == 'None':
        influx_query = f"""
            SELECT *
            FROM "{ dlmeas }"
            WHERE
                time >= '{ start_string }'
                AND time <= '{ end_string }'
        """
    else:
        bucket_devices = BucketDevice.objects.filter(influx_source=source, report_group=report_group)
        dev_eui_list = [device.dev_eui for device in bucket_devices]
        dev_eui_csv = ','.join([f"'{ dev_eui }'" for dev_eui in dev_eui_list])

        influx_query = f"""
            SELECT *
            FROM "{ dlmeas }"
            WHERE
                dev_eui IN ({ dev_eui_csv })
                AND time >= '{ start_string }'
                AND time <= '{ end_string }'
        """

    # start_timer = perf_counter()
    with InfluxDBClient3(token=influx_token,
                         host=influx_url,
                         org=influx_org,
                         database=influx_bucket) as client:
        reader = client.query(query=influx_query, language="sql")
        # stop_timer = perf_counter()
    # query_time = round(stop_timer - start_timer, 1)

    influx_pdf = reader.to_pandas()

    if influx_pdf.empty:
        raise ValueError(F"No Downlinks - Measurement: {dlmeas}")

    influx_pdf = influx_pdf.dropna(axis=1, how='all')

    # packet time is as stamped by NS (I believe). If it is available, it is the correct Time for the record.
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
            'datarate': 'Int64'
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
    # this re-orders, and filters column names
    downlink_cols = [
        'time',  'packet_time', 'tx_time','dev_eui', 'counter_down',
        'gateway', 'confirmed', 'ack',
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
