from django.contrib.auth.decorators import login_required
# from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from celery.result import AsyncResult

import matplotlib.pyplot as plt

import pandas as pd
import json
import redis
# from icecream import ic

from device.models import InfluxSource
from surveyor.utils import getGraph, graphSetUp
import numpy as np


@login_required
def bucketDevicesPdr(request):
    """
    This view provides a histogram of Packet Delivery Rate (PDR)
    """
    # setup the context
    task_id = request.GET.get('task_id', None)
    if task_id is None:
        return HttpResponse('No Task_ID was given.')
    task = AsyncResult(task_id)

    if task.state != 'SUCCESS':
        # pass task.state as report_status if NOT SUCCESS
        return HttpResponse(F'<hr>Task State: {task.state}')

    source_id, meas, start_mark, end_mark = eval(task.args)
    report_status, totals_dict = task.result

    source = InfluxSource.objects.get(pk=source_id)
    source_name = source.name

    if report_status.lower().startswith(("failed", "empty")):
        return HttpResponse(F'Report Status: {report_status}')

    redis_client = redis.Redis(host='redis', port=6379, db=0)

    # reconstitute the dataframes from redis

    device_uplinks_json = redis_client.get(f'{task_id}:device_uplinks_df')
    device_uplinks_dict = json.loads(device_uplinks_json)
    device_uplinks_df = pd.DataFrame(device_uplinks_dict)
    # fix the timestamps

    context = {
        'report_status': report_status,
        'source_id': source_id,
        'source_name': source_name,
        'meas': meas,
        'start_mark': start_mark,
        'end_mark': end_mark,
    }

    # Packet Delivery Ratio (PDR)

    graphSetUp(width=10, height=6)
    bins = np.arange(0, 1.05, 0.05)

    # Creating the histogram
    counts, edges, bars = plt.hist(device_uplinks_df['uplinks_pdr'],
                                   bins=bins,
                                   edgecolor='black',
                                   align='mid',
                                   )

    plt.bar_label(bars)

    plt.xlabel('Uplink - Packet Delivery Ratio (PDF)')
    plt.ylabel('Devices')
    plt.title('Packet Delivery Ratio (PDR) Distribution')
    plt.grid(True)
    plt.xlim(0, 1)
    plt.ylim(0, None)
    plt.tight_layout()

    pdr_hist = getGraph()

    context["pdr_hist"] = pdr_hist

    rendered = render_to_string('performer/bucketDevicesPdr.html', context)

    return HttpResponse(rendered)
