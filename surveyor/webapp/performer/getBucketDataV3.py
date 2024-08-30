# from django.conf import settings
import pandas as pd
import dateutil.parser
import dateutil.tz
from influxdb_client_3 import InfluxDBClient3

from device.models import InfluxSource, BucketDevice

from icecream import ic
from time import perf_counter


def getBucketDataV3(source_id, meas, start_mark, end_mark, report_group):
    source = InfluxSource.objects.get(pk=source_id)

    influx_url = f"https://{source.host}"

    zulu_tz = dateutil.tz.gettz('UTC')
    start_zulu = dateutil.parser.parse(start_mark).replace(tzinfo=zulu_tz)
    start_string = start_zulu.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_zulu = dateutil.parser.parse(end_mark).replace(tzinfo=zulu_tz)
    end_string = end_zulu.strftime("%Y-%m-%dT%H:%M:%SZ")
    # ic(start_string)
    # ic(end_string)

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
        # ic(dev_eui_csv)
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

    # ic(influx_query)

    start_timer = perf_counter()
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

    stop_timer = perf_counter()
    query_time = round(stop_timer - start_timer, 1)
    # ic(query_time)

    if influx_pdf.empty:
        raise ValueError(F"Dataframe is Empty - check measurement name: {meas}")

    if influx_pdf.shape[0] == 0:
        report_status = "Empty"
        return report_status, influx_pdf

    influx_pdf = influx_pdf.dropna(axis=1, how='all')

    # ic(influx_pdf.info())

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
