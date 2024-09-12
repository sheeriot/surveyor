# from time import perf_counter
import numpy as np
import pandas as pd
import redis
import json
import matplotlib.pyplot as plt
import dateutil.tz

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from celery.result import AsyncResult

from device.models import InfluxSource
from surveyor.utils import getGraph

from icecream import ic


@login_required
def bucketDevicesGwInfo(request):
    """
    This function takes in the device summary dataframe and the device gateway dataframe and returns a folium map.
    """

    task_id = request.GET.get('task_id', None)
    zulu_tz = dateutil.tz.gettz('UTC')

    if task_id is None:
        return HttpResponse('No Task_ID was given.')
    task = AsyncResult(task_id)

    args = task.args.strip("()").split(", ")
    source_id = int(args[0])
    source = InfluxSource.objects.get(id=source_id)

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

        totals_dict_json = redis_client.get(f'{task_id}:totals_dict')
        totals_dict = json.loads(totals_dict_json)
        totals_dict['frame_first'] = dateutil.parser.parse(totals_dict['frame_first']).replace(tzinfo=zulu_tz)
        totals_dict['frame_last'] = dateutil.parser.parse(totals_dict['frame_last']).replace(tzinfo=zulu_tz)

    else:
        return HttpResponse(F'<hr>Task State: {report_status} - no Gateway Info')

    context = {
        'report_status': report_status,
        'source_name': source.name
    }

    # Process Channel Plan
    cp = source.channel_plan

    if cp is None:
        cp_freqs = []
        channelplan = False
        context['channelplan'] = None
    else:
        cp_freqs = cp.freqs.split(',')
        cp_freqs_df = pd.DataFrame(cp_freqs, columns=['freq'])
        channelplan = True
        channelplan_name = cp.name
        context['channelplan'] = channelplan_name

    # channels_seen = gw_freqs_df.drop(['gateway','frames'], axis=1).columns.to_list()

    # first the total_freqs

    total_freqs = gw_freqs_df.drop(['gateway', 'frames'], axis=1).sum()
    total_freqs.name = 'count'
    total_freqs.index.name = 'freq'
    total_freqs = total_freqs.to_frame()
    total_freqs['count'] = total_freqs['count'].astype(int)

    if channelplan:
        freqs_in_df = total_freqs[total_freqs.index.isin(cp_freqs)]
        freqs_in_df = cp_freqs_df.merge(freqs_in_df, on='freq', how='outer').fillna(0)
        freqs_in_df['count'] = freqs_in_df['count'].astype(int)

    # out of channel plan
    freqs_out_df = total_freqs[~total_freqs.index.isin(cp_freqs)].reset_index()

    if gw_info_df.shape[0] != 0:
        gw_info_df = gw_info_df.set_index('gateway')

    # ==== Gateway / Device Counts
    devices_per_gateway = device_gw_df.groupby('gateway')['dev_eui'].nunique().astype(int)
    gw_info_df = gw_info_df.join(devices_per_gateway)
    gw_info_df = gw_info_df.rename(columns={'dev_eui': 'devices'})
    # pass gw_info_df to context for template
    gw_info_df = gw_info_df.reset_index().sort_values('devices', ascending=False)

    context['gw_info_df'] = gw_info_df

    device_total = totals_dict['device_count']
    gateway_total = totals_dict['gateway_count']

    context['device_total'] = device_total
    context['gateway_total'] = gateway_total
    # get Ceiling of 5%
    gw_device_min = device_total // 20
    context['gw_device_min'] = gw_device_min

    # now some graphs
    gw_device_counts = gw_info_df[['gateway', 'devices']].sort_values(['devices'])

    # TOP = filter In gateways with more than 5% of devices
    gw_device_counts_top = gw_device_counts[gw_device_counts['devices'] > gw_device_min]

    top_gateways = gw_device_counts_top['gateway'].unique().tolist()
    gw_freqs_top_df = gw_freqs_df[gw_freqs_df['gateway'].isin(top_gateways)]

    # Horizontal Bar Graph
    gw_device_counts_top = gw_device_counts_top.reset_index()
    x = gw_device_counts_top['gateway']
    y = gw_device_counts_top['devices']

    fig, ax = plt.subplots()
    fig.set_figwidth(12)

    width = 0.8  # the width of the bars
    ind = np.arange(len(y))  # the x locations for the groups
    bar_plot = ax.barh(ind, y, width, color="green", align='edge')
    ax.set_yticks(ind+width/2)
    ax.set_yticklabels(x, minor=False)

    def autolabel(bar_plot):
        for idx, rect in enumerate(bar_plot):
            ax.text(0.25, idx+.25, y[idx], color='white')
    autolabel(bar_plot)

    plt.margins(0, 0.05)
    plt.title(f'{ gw_device_counts_top.shape[0] } gateways with more than { gw_device_min } (5%) of devices ({ device_total })')
    plt.ylabel('Gateway')
    device_counts = getGraph()
    plt.close()
    context['device_counts'] = device_counts

    if channelplan:
        freqs_in_df = freqs_in_df.set_index('freq')
        # ic(freqs_in_df.info())
        plt.figure(figsize=(10, 2))
        freqs_in_df.plot.bar(width=0.9, color='green')
        plt.title("In-Channel Plan - Received by Frequency")
        plt.xlabel("Frequency")
        plt.ylabel("Count")
        freqs_in_bar = getGraph()
        plt.close()
        context["freqs_in_bar"] = freqs_in_bar

        freqs_in_df = freqs_in_df.T
        freqs_in_df.columns = freqs_in_df.columns.astype(str)
        context['freqs_in_df'] = freqs_in_df

    if freqs_out_df.shape[0] > 0:
        freqs_out_df = freqs_out_df.set_index('freq')

        plt.figure(figsize=(10, 2))
        freqs_out_df.plot.bar(width=0.9, color='red')
        plt.title("NOT In-Channel Plan - Received by Frequency")
        plt.xlabel("Frequency")
        plt.ylabel("Count")
        freqs_out_bar = getGraph()
        plt.close()
        context["freqs_out_bar"] = freqs_out_bar

        if freqs_out_df.shape[0] > 0:
            freqs_out_df = freqs_out_df.T
            freqs_out_df.columns = freqs_out_df.columns.astype(str)
            context['freqs_out_df'] = freqs_out_df

    total_freqs = total_freqs.T
    total_freqs.columns = total_freqs.columns.astype(str)
    context['total_freqs'] = total_freqs

    # put all gateway graphs on same Y limit

    max_count = gw_freqs_df.drop(['gateway', 'frames'], axis=1).max().max()
    max_yaxis = (max_count * 1.05).astype(int)

    # Create a bar chart for each gateway in gw_freqs_df
    # create a subset for display instead of full index of gateways
    gw_freq_bars = []
    gw_freqs_top_df = gw_freqs_top_df.set_index('gateway')
    for gateway in gw_freqs_top_df.index:
        plt.figure(figsize=(14, 2))
        freqs = gw_freqs_top_df.loc[gateway].drop('frames')
        freqs.plot.bar(width=0.9)
        plt.title(f"GW: {gateway} - Frames Received by Frequency")
        plt.xlabel("Frequency")
        plt.ylabel("Count")
        plt.ylim(0, max_yaxis)
        gw_freq_bars.append(getGraph())
        plt.close()

    context['gw_freq_bars'] = gw_freq_bars

    rendered = render_to_string('performer/bucketDevicesGwInfo.html', context)

    return HttpResponse(rendered)
