import matplotlib.pyplot as plt
import base64
from io import BytesIO

from datetime import datetime, timedelta

import pytz
# import django.utils.timezone as tz
# from django.conf import settings
# from icecream import ic


def getGraph():
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    graph = base64.b64encode(image_png)
    graph = graph.decode('utf-8')
    buffer.close()
    return graph


def graphSetUp(width=8, height=5):
    plt.switch_backend('AGG')
    plt.rcParams['figure.figsize'] = (width, height)

# def getInfluxRfData(endNode,start_at,end_at):
#     src = endNode.influx_source
#     url = f"https://{src.host}/{src.path}"
#     params = {}
#     params['db'] = src.dbname
#     start_at_str = start_at.astimezone(tz.utc).strftime("%Y-%m-%d %H:%M:%S")
#     end_at_str = end_at.astimezone(tz.utc).strftime("%Y-%m-%d %H:%M:%S")
#     select = f"SELECT f_count,counter_up,gateway_eui,gateway,rssi,snr, \
#                 frequency,spreading_factor,rcv_time,rx_time,frame_size, message_type \
#                 FROM {endNode.influx_measurement} \
#                 WHERE dev_eui = '{endNode.dev_eui.lower()}' \
#                 and time > '{start_at_str}' and time < '{ end_at_str }'"
#     params['q'] = select
#     if src.v2:
#         params['org'] = src.influx_org
#         headers = {'Authorization': 'Token ' + src.influx_token }
#         raw_data = requests.get(url, params=urlencode(params), headers=headers)

#     else:
#         raw_data = requests.get(url, params=urlencode(params), auth=(src.influx_user, src.influx_pass))

#     if raw_data.status_code == 401:
#         raise ValueError("401: InfluxDB Authentication Error")

#     df_f = pd.read_json(BytesIO(raw_data.content))
#     results = df_f.results[0]

#     if "error" in results:
#         error_message = results['error']
#         raise ValueError(error_message)

#     try:
#         columns = df_f["results"][0]["series"][0]["columns"]
#         data = df_f["results"][0]["series"][0]["values"]
#     except KeyError: #if no new entries
#         columns = []
#         data = []

#     # move this back into Pandas Data Frame (DF) for easy graphing (line definition)
#     # clearly this extract can be done better
#     #print("Influx Query - Result Length: ", len(data))
#     df = pd.DataFrame(data,columns=columns)
#     # convert to time objects for time series graphing
#     if data:
#         df['time'] = pd.to_datetime(df['time'])
#         #df['rcv_time'] = pd.to_datetime(df['rcv_time'])

#     #ensure that the numbering of the columns is a continuos range
#     #problems caused itereating over them otherwise
#     df = df.reset_index(drop=True)

#     if not df.empty:
#         df.sort_values(by=['rcv_time'], inplace=True)

#     return(df)


def init_datetime(tz):
    now = datetime.now(pytz.timezone(tz))
    yesterday = now - timedelta(1)
    yesterday_formatted = yesterday.strftime("%Y-%m-%dT00:00")
    current_time = now.strftime("%Y-%m-%dT%H:%M")
    # print(current_time)
    return (yesterday_formatted, current_time)


def init_datetime_daysago(tz, days_ago):
    now = datetime.now(pytz.timezone(tz))
    begindate = now - timedelta(days_ago)
    begindate = begindate.strftime("%Y-%m-%dT00:00")
    current_time = now.strftime("%Y-%m-%dT%H:%M")
    return (begindate, current_time)


def computed_rssi(rssi, snr):
    computed_rssi = round(rssi + (snr <= -5) * snr + ((snr > -5) & (snr < 10)) * (snr / 3 - 10 / 3))
    return computed_rssi
