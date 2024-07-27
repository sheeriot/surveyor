# from django.conf import settings

import pandas as pd
import dateutil.parser
import dateutil.tz

from influxdb_client import InfluxDBClient
from device.models import InfluxSource, BucketDevice
# from icecream import ic


def getBucketData(source_id, meas, start_mark, end_mark, report_group):
    source = InfluxSource.objects.get(pk=source_id)
    influx_url = f"https://{source.host}"
    zulu_tz = dateutil.tz.gettz('UTC')
    start_zulu = dateutil.parser.parse(start_mark).replace(tzinfo=zulu_tz)
    start_string = start_zulu.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_zulu = dateutil.parser.parse(end_mark).replace(tzinfo=zulu_tz)
    end_string = end_zulu.strftime("%Y-%m-%dT%H:%M:%SZ")

    if report_group == 'None':
        dev_eui_regex = '.*'

    else:
        bucket_devices = BucketDevice.objects.filter(influx_source=source, report_group=report_group)

        dev_eui_list = [device.dev_eui for device in bucket_devices]

        dev_eui_list_str = '|'.join([f'{ dev_eui }' for dev_eui in dev_eui_list])
        dev_eui_regex = f"^({ dev_eui_list_str })$"

    influx_query = f'''
        from(bucket: "{source.dbname}")
            |> range(start: {start_string}, stop: { end_string })
            |> filter(fn:(r) => r._measurement == "{ meas }")
            |> filter(fn: (r) => r.dev_eui =~ /{ dev_eui_regex }/)
            |> drop(fn: (column) => column =~ /^_(start|stop|measurement)/)
            |> pivot(rowKey:["dev_eui","_time"], columnKey: ["_field"], valueColumn: "_value")
            |> keep(columns: ["_time","dev_eui","gateway","gateway_eui",
                    "rx_time","rcv_time",
                    "device_addr","counter_up",
                    "duplicate","frame_size","payload_size",
                    "bandwidth","datarate","payload_size",
                    "spreading_factor","rssi","snr","frequency","gw_latitude","gw_longitude",
                    "tag1","tag2","pluscode"])
        '''

    with InfluxDBClient(
                        url=influx_url,
                        token=source.influx_token,
                        org=source.influx_org,
                        timeout=(5000, 60000)
                        ) as client:
        try:
            influx_pdf = client.query_api().query_data_frame(org=source.influx_org, query=influx_query)
        except Exception as e:
            report_status = F'Failed: {e}'
            return report_status, pd.DataFrame()

    # this normalizes the list into a DF by adding missing columns and appending
    if type(influx_pdf) is list:
        append_flag = False
        df_list = influx_pdf
        columns_set = set([col for df in df_list for col in df.columns])
        frames_df = pd.DataFrame()
        for pdf in df_list:
            missing_cols = columns_set - set(pdf.columns)
            pdf = pdf.reindex(columns=pdf.columns.tolist() + list(missing_cols))
            if append_flag:
                frames_df = pd.concat([frames_df, pdf], axis=0)
            else:
                frames_df = pdf
                append_flag = True
        influx_pdf = frames_df.reset_index(drop=True)

    if influx_pdf.shape[0] == 0:
        report_status = "Empty"
        return report_status, influx_pdf

    influx_pdf = influx_pdf.drop(columns=['result', 'table'])

    # fix a few inconsistent column names
    if 'rx_time' not in influx_pdf.columns and 'rcv_time' in influx_pdf.columns:
        influx_pdf = influx_pdf.rename(columns={'rcv_time': 'rx_time'})
    if 'gateway' not in influx_pdf.columns and 'gateway_eui' in influx_pdf.columns:
        influx_pdf = influx_pdf.rename(columns={'gateway_eui': 'gateway'})
    if 'device_addr' not in influx_pdf.columns:
        influx_pdf['device_addr'] = 'not'

    # make a copy for return
    pdf = influx_pdf.copy().sort_values(by=['dev_eui', '_time']).reset_index(drop=True)

    # Setup Data Types in dataframe
    pdf = pdf.astype({
        'counter_up': 'Int64',

        'spreading_factor': 'Int64',
        'rssi': 'Int64',
        'frequency': 'string',
    })
    if 'rx_time' in pdf.columns:
        pdf = pdf.astype({'rx_time': 'string'})
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
