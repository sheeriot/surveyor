# from time import perf_counter
import numpy as np
import pandas as pd
import redis
import json
import matplotlib.pyplot as plt

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from celery.result import AsyncResult

from surveyor.utils import getGraph

# from icecream import ic


@login_required
def bucketDevicesGwInfo(request):
    """
    This function takes in the device summary dataframe and the device gateway dataframe and returns a folium map.
    """

    task_id = request.GET.get('task_id', None)

    if task_id is None:
        return HttpResponse('No Task_ID was given.')
    task = AsyncResult(task_id)

    if task.state == 'SUCCESS':
        report_status, totals_dict = task.result
        if report_status.lower().startswith(("failed", "empty")):
            return HttpResponse(F'Report Status: {report_status}')

        redis_client = redis.Redis(host='redis', port=6379, db=0)

        # reconstitute the dataframes from redis
        gw_info_json = redis_client.get(f'{task_id}:gw_info_df')
        gw_info_dict = json.loads(gw_info_json)
        gw_info_df = pd.DataFrame(gw_info_dict)

        device_gw_json = redis_client.get(f'{task_id}:device_gw_df')
        device_gw_dict = json.loads(device_gw_json)
        device_gw_df = pd.DataFrame(device_gw_dict)

        gw_freqs_json = redis_client.get(f'{task_id}:gw_freqs_df')
        gw_freqs_dict = json.loads(gw_freqs_json)
        gw_freqs_df = pd.DataFrame(gw_freqs_dict)

    else:
        return HttpResponse(F'<hr>Task State: {report_status} - no Gateway Info')

    context = {
        'report_status': report_status,
    }

    gw_info_df = gw_info_df.set_index('gateway')

    # create an indexed Pandas series on gateway
    devices_per_gateway = device_gw_df.groupby('gateway')['dev_eui'].nunique().astype(int)
    gw_info_df = gw_info_df.join(devices_per_gateway)
    gw_info_df = gw_info_df.rename(columns={'dev_eui': 'devices'})
    # pass gw_info_df to context for template
    context['gw_info_df'] = gw_info_df.reset_index().sort_values('devices', ascending=False)

    # now some graphs
    gw_device_counts = gw_info_df[['devices']].sort_values(['devices']).reset_index()

    x = gw_device_counts['gateway']
    y = gw_device_counts['devices']

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.set_figwidth(14)

    width = 0.75  # the width of the bars
    ind = np.arange(len(y))  # the x locations for the groups
    bar_plot = ax.barh(ind, y, width, color="green", align='edge')
    ax.set_yticks(ind+width/2)
    ax.set_yticklabels(x, minor=False)

    def autolabel(bar_plot):
        for idx, rect in enumerate(bar_plot):
            ax.text(0.25, idx+.25, y[idx], color='white')
    autolabel(bar_plot)

    plt.margins(0, 0.05)
    plt.title('Devices per Gateway')
    plt.ylabel('Gateway')

    # plt.show()
    device_counts = getGraph()

    context['device_counts'] = device_counts

    context['gw_freqs_df'] = gw_freqs_df
    gw_freqs_df = gw_freqs_df.set_index('gateway')
    # now some bar charts for frequency distribution
    # first the totals

    total_freqs = gw_freqs_df.drop('frames', axis=1).sum()

    plt.figure(figsize=(14, 2))
    total_freqs.plot.bar(width=0.9)
    plt.title("Total Frames Received by Frequency")
    plt.xlabel("Frequency")
    plt.ylabel("Count")

    freqs_bar = getGraph()
    context["freqs_bar"] = freqs_bar

    # put all gateway graphs on same Y limit

    max_count = gw_freqs_df.drop('frames', axis=1).max().max()
    max_yaxis = (max_count * 1.05).astype('int')

    # Create a bar chart for each gateway in gw_freqs_df
    # create a subset for display instead of full index of gateways
    gw_freq_bars = []
    for gateway in gw_freqs_df.index:
        plt.figure(figsize=(14, 2))
        freqs = gw_freqs_df.loc[gateway].drop('frames')
        freqs.plot.bar(width=0.9)
        plt.title(f"GW: {gateway} - Frames Received by Frequency")
        plt.xlabel("Frequency")
        plt.ylabel("Count")
        plt.ylim(0, max_yaxis)
        gw_freq_bars.append(getGraph())

    context['gw_freq_bars'] = gw_freq_bars

    rendered = render_to_string('performer/bucketDevicesGwInfo.html', context)

    return HttpResponse(rendered)
