import matplotlib.pyplot as plt
import base64
from io import BytesIO
import pytz
import pandas as pd

from datetime import datetime, timedelta
from geopy.distance import geodesic

from icecream import ic


def geoDistance(lat1, long1, lat2, long2):
    if any([pd.isnull(lat1), pd.isnull(long1), pd.isnull(lat2), pd.isnull(long2)]):
        return None
    # ic(pd.isnull(lat1), type(long1), lat2, long2)
    dist = round(geodesic((lat1, long1), (lat2, long2)).km, 3)
    return dist


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
