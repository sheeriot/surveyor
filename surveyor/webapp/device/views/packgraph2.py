from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.utils import timezone

import dateutil.parser
import dateutil.tz

from surveyor.settings import TIME_ZONE
from ..form_endnode2 import endNodeSelect2
from accounts.models import Person
from surveyor.utils import graphSetUp, getGraph, init_datetime_daysago
from ..models import EndNode
from ..getDeviceData import getDeviceFrames, getDownlinks
from ..deviceFramesFun import device_summ_frames, getDeviceFreqs

from icecream import ic
from time import perf_counter

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib as mpl
import pandas as pd

# =================
# packGraph View - Parse the Input Data First
# =================


@login_required
def packgraph2(request, deveui='', **kwargs):
    username = request.user
    person = Person.objects.get(username=username)
    orgs_list = person.orgs_list()

    # timezone stuff
    if timezone.get_current_timezone():
        tz = str(timezone.get_current_timezone())
    else:
        tz = TIME_ZONE
    timezone.activate(tz)
    zulu_tz = dateutil.tz.gettz('UTC')
    local_tz = dateutil.tz.gettz(tz)

    console_messages = []
    console_messages.append(F'Local Timezone: {tz}')

    if request.method == 'GET' and 'submit' in request.GET:
        form = endNodeSelect2(request.GET, orgs_list=orgs_list)
        if form.is_valid():
            start = form.cleaned_data["start"]
            start_zulu = start.astimezone(zulu_tz)
            end = form.cleaned_data["end"]
            end_zulu = end.astimezone(zulu_tz)
            endnode = form.cleaned_data["endnode"]
            endnode_id = endnode.id
            dev_eui = endnode.dev_eui.lower()
            source = endnode.influx_source
            source_id = source.id
            meas = endnode.influx_measurement

        else:
            # form validation failed. Provide messages
            console_messages.append(F'Form Invalid: {form.errors}')
            console_messages.append(F'Form Data: {form.data}')
            console_messages.append(F'Form Cleaned Data: {form.cleaned_data}')
            console_messages.append(F'Kwargs: {kwargs}')
            context = {
                'form': form,
                'console_messages': console_messages,
                'results_display': False,
                'error_message': form.errors
            }
            return render(request, 'device/packgraph2.html', context)

    # got some kwargs from URL, but no submit button, process them
    elif request.method == 'GET' and kwargs:
        start_default, end_default = init_datetime_daysago(tz, 3)

        if 'endnode_id' in kwargs:
            endnode_id = kwargs.pop('endnode_id')
            endnode = EndNode.objects.get(pk=endnode_id)

        if 'start_mark' in kwargs:
            start_mark = kwargs.pop('start_mark')
            start_zulu = dateutil.parser.parse(start_mark).replace(tzinfo=zulu_tz)
            start = start_zulu.astimezone(local_tz)
        else:
            start = start_default

        if 'end_mark' in kwargs:
            end_mark = kwargs.pop('end_mark')
            end_zulu = dateutil.parser.parse(end_mark).replace(tzinfo=zulu_tz)
            end = end_zulu.astimezone(local_tz)
        else:
            end = end_default

        form = endNodeSelect2({
            'endnode': endnode_id,
            'start': start,
            'end': end},
            orgs_list=orgs_list
        )

        if form.is_valid():
            start = form.cleaned_data["start"]
            start_zulu = start.astimezone(zulu_tz)
            end = form.cleaned_data["end"]
            end_zulu = end.astimezone(zulu_tz)
            endnode_id = form.cleaned_data["endnode"].id
            endnode = EndNode.objects.get(pk=endnode_id)
            dev_eui = endnode.dev_eui.lower()
            source = endnode.influx_source
            source_id = source.id
            meas = endnode.influx_measurement
        else:
            # form validation failed. Provide messages
            console_messages.append(F'Form Invalid: {form.errors}')
            console_messages.append(F'Form Data: {form.data}')
            console_messages.append(F'Form Cleaned Data: {form.cleaned_data}')
            console_messages.append(F'Kwargs: {kwargs}')
            context = {
                'form': form,
                'console_messages': console_messages,
                'results_display': False,
                'error_message': form.errors
                }
            return render(request, 'device/packgraph2.html', context)

    elif request.method == 'GET':

        start_default, end_default = init_datetime_daysago(tz, 3)
        form = endNodeSelect2(
            initial={
                'start': start_default,
                'end': end_default},
            orgs_list=orgs_list
        )
        context = {
            'form': form,
            'console_messages': console_messages,
            'results_display': False,
        }
        return render(request, 'device/packgraph2.html', context)

    # ------ being here means we have a valid form ------
    start_mark = start_zulu.strftime('%Y%m%dT%H%MZ')
    end_mark = end_zulu.strftime('%Y%m%dT%H%MZ')

    context = {
        'form': form,
        'start': start,
        'start_mark': start_mark,
        'end': end,
        'end_mark': end_mark,
        'dev_eui': dev_eui,
        'endnode': endnode,
        'source': source,
        'source_id': source_id,
        'source_name': source.name,
        'meas': meas,
    }
    # get the channel plan setup
    cp = source.channel_plan

    if cp is None:
        cp_freqs = []
        # cp_freqs_df = pd.DataFrame()
        channelplan = False
        context['channelplan'] = None

    else:
        cp_freqs = cp.freqs.split(',')
        cp_freqs_df = pd.DataFrame(cp_freqs, columns=['freq'])
        channelplan = True
        channelplan_name = cp.name
        context['channelplan'] = channelplan_name

    start_timer = perf_counter()
    try:
        frames_df = getDeviceFrames(source_id, meas, dev_eui, start_zulu, end_zulu)
    except ValueError as err:
        console_messages.append(F'Cannot getDeviceFrames: {err}')
        error_message = F'Cannot getDeviceFrames: {err}'
        context['results_display'] = False
        context['error_message'] = error_message
        context['console_messages'] = console_messages
        return render(request, 'device/packgraph2.html', context)

    stop_timer = perf_counter()
    query_time = round(stop_timer - start_timer, 1)
    console_messages.append(F'Source Query Time: {query_time}')

    if frames_df.empty:
        console_messages.append('No data found')
        error_message = 'No data found'
        context['results_display'] = False
        context['error_message'] = error_message
        context['console_messages'] = console_messages
        return render(request, 'device/packgraph2.html', context)

    context['results_display'] = True
    context['frames_received'] = frames_df.shape[0]
    context['frames_first'] = frames_df['time'].min()
    context['frames_last'] = frames_df['time'].max()
    # ic(frames_df.info())

    # summarize the frames into device_uplinks_df
    frames_df, device_uplinks_df = device_summ_frames(frames_df)

    # Device Frequency Counts
    device_freqs_df = getDeviceFreqs(device_uplinks_df)
    # in channel plan
    if channelplan:
        device_freqs_in_df = device_freqs_df[device_freqs_df['freq'].isin(cp_freqs)]
        device_freqs_in_df = cp_freqs_df.merge(device_freqs_in_df, on='freq', how='outer').fillna(0)
        device_freqs_in_df['count'] = device_freqs_in_df['count'].astype(int)

        context['device_freqs_in_df'] = device_freqs_in_df.T
    # out of channel plan
    device_freqs_out_df = device_freqs_df[~device_freqs_df['freq'].isin(cp_freqs)]

    context['device_freqs_out_df'] = device_freqs_out_df.T

    # Now the Gateways
    context['gateway_count'] = frames_df.gateway.nunique()
    if 'gw_latitude' in frames_df.columns and 'gw_longitude' in frames_df.columns:
        gw_loc_df = frames_df[['gateway', 'gw_latitude', 'gw_longitude']].dropna().drop_duplicates(subset=['gateway'])
        gw_loc_df = gw_loc_df.rename(columns={'gw_latitude': 'lat', 'gw_longitude': 'long'})
        gw_loc_df = gw_loc_df.set_index('gateway')
        # gw_loc_df.to_csv(f'{path_out}/{env_name}_gw_locs_{runstamp}.csv')
    else:
        console_messages.append('No gateway locations found')
        gw_loc_df = pd.DataFrame()
    context['gateway_loc_df'] = gw_loc_df

    # Localize the time for views and pass on frames an uplinks dataframes
    frames_df['time'] = frames_df['time'].dt.tz_convert(local_tz)
    frames_out_df = frames_df.copy()
    if 'gw_lat' and 'gw_long' in frames_out_df.columns:
        frames_out_df[['gw_lat', 'gw_long']] = frames_out_df[['gw_lat', 'gw_long']].fillna('')

    context['frames_df'] = frames_out_df

    device_uplinks_df['time'] = device_uplinks_df['time'].dt.tz_convert(local_tz)

    device_uplinks_out_df = device_uplinks_df.copy().drop(columns=['tgap'])

    device_uplinks_out_df = device_uplinks_out_df.rename(columns={'tgapf': 'tgap'})
    # ic(device_uplinks_out_df.info())

    context['device_uplinks_df'] = device_uplinks_out_df

    # === Create Summary Data
    context['uplinks_received'] = device_uplinks_df.shape[0]
    context['uplinks_missed'] = device_uplinks_df['missed'].sum()

    uplinks_pdr = round(context['uplinks_received']/(context['uplinks_received']+context['uplinks_missed']), 3)
    context['uplinks_pdr'] = uplinks_pdr

    # how many joins sequences total
    join_seqs = device_uplinks_df['addr'].nunique()
    context['rejoins'] = join_seqs - 1
    rejoins_df = frames_df[['addr', 'count', 'time']].drop_duplicates(["addr"], keep='first')
    # drop first in sequence as it is NOT a rejoin
    rejoins_df = rejoins_df.tail(-1)
    context['rejoins_df'] = rejoins_df

    # ================================================================
    # now the scatter plot
    mpl.rcParams['timezone'] = tz
    # WTF
    graphSetUp(width=10, height=6)

    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()
    ax1.set_zorder(ax2.get_zorder()+1)
    ax1.patch.set_visible(False)
    fig.patch.set_facecolor('#ECECEC')
    ax1.set_facecolor('#ECECEC')

    fig.suptitle(f"{endnode.name}\nDevEUI: {endnode.dev_eui}", fontsize=14, fontweight='bold')
    ax1.set_title(f"RF Uplink Performance: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')}")
    ax1.set_ylabel("SNR/Misses")
    ax1.set_xlabel("Time")
    ax2.set_ylabel("RSSI")

    myFmt = mdates.HourLocator('%H')
    myFmt = mdates.AutoDateFormatter(myFmt)
    ax1.xaxis.set_major_formatter(myFmt)
    # ax1.set_xticklabels(times,rotation=90)

    # add text
    ax2.text(
        0.5, 0.1,
        F'Uplinks Received: {context["uplinks_received"]}, '
        F'Missed: {context["uplinks_missed"]}, '
        F'Delivery Ratio ({round(context["uplinks_pdr"]*100,1)}%)',
        verticalalignment='center',
        horizontalalignment='center',
        transform=ax1.transAxes,
        color='darkred',
        alpha=0.9,
        fontsize=10,
        bbox=dict(facecolor='cornsilk', edgecolor='black', pad=5.0),
    )
    # X axis limits
    ax1.set_xlim(context['start'], context['end'])
    ax1.grid(False)
    # enable X-Axis grid
    ax1.xaxis.grid(True)

    # Y axis limits
    ax1.set_ylim([-20, 15])
    ax2.set_ylim([-140, -35])
    # y axis, set ticks
    ax1.set_yticks([-20, -15, -10, -5, 0, 5, 10, 15])
    ax2.set_yticks([-140, -125, -110, -95, -80, -65, -50, -35])

    if 'helium' in frames_df.columns:
        helium_frames_df = frames_df[frames_df['helium']]
        everynet_frames_df = frames_df[~frames_df['helium']]
        helium = True
    else:
        everynet_frames_df = frames_df
        helium_frames_df = pd.DataFrame()
        helium = False

    # Now Downlinks
    if endnode.downlinks is True:
        dlmeas = endnode.influx_measurement_downlinks
        try:
            downlinks_df = getDownlinks(source_id, dlmeas, dev_eui, start_zulu, end_zulu)
            downlinks_df['time'] = downlinks_df['time'].dt.tz_convert(local_tz)
            downlinks_df['tx_time'] = downlinks_df['tx_time'].dt.tz_convert(local_tz)
            context['downlinks_df'] = downlinks_df

        except ValueError as err:
            console_messages.append(F'{err}')
            context['downlinks_df'] = pd.DataFrame()

    else:
        context['downlinks_df'] = pd.DataFrame()
    # plotting

    l2 = ax1.scatter(frames_df['time'], frames_df['snr'],
                     marker='o', color='dodgerblue', s=16, clip_on=False)
    legend_lines = (l2,)
    legend_text = ('SNR',)

    l1 = ax2.scatter(everynet_frames_df['time'], everynet_frames_df['rssi'],
                     marker='2', color='green', s=30, clip_on=False)
    legend_lines = legend_lines + (l1,)
    legend_text = legend_text + ('RSSI',)

    if helium:
        l6 = ax2.scatter(helium_frames_df['time'], helium_frames_df['rssi'],
                         marker='$H$', c='brown', s=30, clip_on=False)
        legend_lines = legend_lines + (l6,)
        legend_text = legend_text + ('Helium',)

    missmarks_df = device_uplinks_df.loc[device_uplinks_df['missed'] > 0]
    l3 = ax1.scatter(missmarks_df['time'], missmarks_df['missed'],
                     marker='3', color='crimson',
                     s=100, clip_on=False
                     )
    legend_lines = legend_lines + (l3,)
    legend_text = legend_text + ('Missed',)

    bigmiss_df = missmarks_df.loc[missmarks_df['missed'] >= 15]
    bigmiss_df['mark'] = 15
    ax1.scatter(bigmiss_df['time'], bigmiss_df['mark'],
                marker='x', color='crimson',
                s=200, clip_on=False
                )

    if not rejoins_df.empty:
        rejoins_df['mark'] = 0
        l4 = ax1.scatter(rejoins_df['time'], rejoins_df['mark'], marker='P', color='fuchsia', s=100)
        legend_lines = legend_lines + (l4,)
        legend_text = legend_text + ('Join',)

    if endnode.downlinks is True:
        downlinks_df['mark'] = 15
        l7 = ax1.scatter(downlinks_df['time'], downlinks_df['mark'],
                         marker='1', c='darkviolet', s=40, clip_on=False)
        legend_lines = legend_lines + (l7,)
        legend_text = legend_text + ('Downlinks',)

    # remove border lines
    ax1.spines['right'].set_visible(False)
    ax1.spines['top'].set_visible(False)
    ax1.spines['left'].set_visible(False)
    ax1.spines['bottom'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax2.spines['bottom'].set_visible(True)

    ax1.tick_params(left=False)
    ax2.tick_params(right=False)
    ax1.tick_params(bottom=False)
    ax2.tick_params(bottom=False)

    # legend
    fig.legend(legend_lines,
               legend_text,
               # loc='upper right',
               bbox_to_anchor=(0.94, 1.0),
               fontsize=8,
               title_fontsize=12,
               facecolor='azure',
               fancybox=True,
               framealpha=0.3,
               edgecolor='black'
               )

    # create grid
    plt.grid(True)
    ax1.xaxis.grid(True)

    graph = getGraph()
    context["graph"] = graph
    plt.close()

    # passing along a graph of Channel Plan hits
    if channelplan:
        graphSetUp(width=10, height=3)
        device_freqs_in_df.plot(x='freq', y='count', kind='bar', color='green', width=0.85, zorder=3)
        plt.xlabel('Frequency')
        # plt.ylabel('Count')
        plt.title('Device Frequencies - In Channel Plan')
        plt.grid(axis='y', zorder=0)
        graph_freqs_in = getGraph()
        context["graph_freqs_in"] = graph_freqs_in
        plt.close()

    # Out of Plan Freqs
    if device_freqs_out_df.shape[0] != 0:
        graphSetUp(width=10, height=3)
        device_freqs_out_df.plot(x='freq', y='count', kind='bar', color='red', width=0.85, zorder=3)
        plt.xlabel('Frequency')
        # plt.ylabel('Count')
        plt.title('Device Frequencies - Out of Channel Plan')
        plt.grid(axis='y', zorder=0)
        graph_freqs_out = getGraph()
        context["graph_freqs_out"] = graph_freqs_out
        plt.close()

    context['console_messages'] = console_messages

    return render(request, 'device/packgraph2.html', context)
