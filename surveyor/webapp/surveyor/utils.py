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
