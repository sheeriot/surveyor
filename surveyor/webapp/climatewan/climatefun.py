# from time import perf_counter
# from icecream import ic
from influxdb_client import InfluxDBClient
from device.models import InfluxSource
import pandas as pd


def getInfluxClimateData(source_id, meas, dev_eui, start, end):
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
        |> keep(columns: ["_time","rx_time","rcv_time",
            "temperature","humidity",
            "battery_voltage","battery_level"])
    """
    # start_timer = perf_counter()

    with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
        influx_pdf = client.query_api().query_data_frame(org=influx_org, query=influx_query)
    # stop_timer = perf_counter()
    # query_time = round(stop_timer - start_timer,1)
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

    # now copy for processing
    frames_df = influx_pdf.copy().reset_index(drop=True)

    if 'rcv_time' in frames_df.columns:
        if 'rx_time' not in frames_df.columns:
            frames_df = frames_df.rename(columns={'rcv_time': 'rx_time'})
        else:
            frames_df = frames_df.drop(columns=['rcv_time'])

    if 'rx_time' in frames_df:
        frames_df['time'] = pd.to_datetime(frames_df['rx_time'], unit='s').dt.tz_localize('UTC')
        frames_df = frames_df.drop(columns=['rx_time'])
        frames_df = frames_df.drop('_time', axis=1)
    else:
        raise ValueError(F"No rx_time: {meas}")

    if 'f_count' in frames_df.columns:
        if 'counter_up' not in frames_df.columns:
            frames_df = frames_df.rename(columns={'gateway_eui': 'gateway'})
        else:
            frames_df = frames_df.drop(columns=['gateway_eui'])

    # check for climate data
    climate_cols = [
        'temperature',
        'humidity',
        'battery_voltage',
        'battery_level'
        ]
    if not any(col in frames_df.columns for col in climate_cols):
        return pd.DataFrame()
    climate_cols = [col for col in climate_cols if col in frames_df.columns]
    frames_df = frames_df.dropna(subset=climate_cols, how='all')

    if 'temperature' in frames_df.columns:
        frames_df['temperature'] = frames_df['temperature'].astype(float)
        frames_df['temperature'] = frames_df['temperature'] * 1.8 + 32.0
        frames_df['temperature'] = frames_df['temperature'].round(1)

    if 'humidity' in frames_df.columns:
        frames_df['humidity'] = frames_df['humidity'].astype(float)
        frames_df['humidity'] = frames_df['humidity'].round(1)

    if 'battery_voltage' in frames_df.columns:
        frames_df['battery_voltage'] = frames_df['battery_voltage'].astype(float)
        frames_df['battery_voltage'] = frames_df['battery_voltage'].round(1)

    if 'battery_level' in frames_df.columns:
        frames_df['battery_level'] = frames_df['battery_level'].astype('Int64')

    # add the time frame to the front of the columns to return
    climate_cols.insert(0, 'time')
    # reorder columns
    frames_df = frames_df[climate_cols].sort_values(by=['time']).reset_index(drop=True)

    return frames_df
