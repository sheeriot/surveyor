from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

import dateutil.parser
import dateutil.tz

from surveyor.settings import TIME_ZONE
from .models import InfluxSource
from .forms import EndNodeForm, bucketDeviceForm
from .getDeviceData import getDeviceFrames
from .deviceFramesFun import device_summ_frames, getDeviceFreqs

from accounts.models import Person
from surveyor.utils import graphSetUp, getGraph, init_datetime_daysago

from icecream import ic
from time import perf_counter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib as mpl
import pandas as pd


@login_required
def addEndNode(request):
    if request.method == 'POST':
        end_node_form = EndNodeForm(request.POST)
        if end_node_form.is_valid():
            end_node_form.save()
            messages.success(request, 'Your device was successfully added!')
        else:
            messages.error(request, ('Error saving device', end_node_form.errors))
        return redirect('addEndNode')
    end_node_form = EndNodeForm()
    username = request.user
    person = Person.objects.get(username=username)
    end_node_form.fields["surveyor_org"].queryset = person.orgs()
    return render(request, 'device/addEndNode.html', {'form': end_node_form})


@login_required
def bucketdevice(request, **kwargs):
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
        form = bucketDeviceForm(request.GET, orgs_list=orgs_list)
        if form.is_valid():
            start = form.cleaned_data["start"]
            start_zulu = start.astimezone(zulu_tz)
            end = form.cleaned_data["end"]
            end_zulu = end.astimezone(zulu_tz)
            source = form.cleaned_data["source"]
            source_id = source.id
            meas = form.cleaned_data["meas"]
            dev_eui = form.cleaned_data["dev_eui"]
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
            return render(request, 'device/bucketdevice.html', context)

    elif request.method == 'GET' and kwargs:
        start_default, end_default = init_datetime_daysago(tz, 3)

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

        if 'source_id' in kwargs:
            source_id = kwargs.pop('source_id')
            source = InfluxSource.objects.get(pk=source_id)
        if 'meas' in kwargs:
            meas = kwargs.pop('meas')
        if 'dev_eui' in kwargs:
            dev_eui = kwargs.pop('dev_eui')

        form = bucketDeviceForm(
            {
             'dev_eui': dev_eui,
             'source': source,
             'meas': meas,
             'start': start,
             'end': end,
            },
            orgs_list=orgs_list
        )
        if form.is_valid():
            dev_eui = form.cleaned_data["dev_eui"]
            source = form.cleaned_data["source"]
            meas = form.cleaned_data["meas"]
            start = form.cleaned_data["start"]
            start_zulu = start.astimezone(zulu_tz)
            end = form.cleaned_data["end"]
            end_zulu = end.astimezone(zulu_tz)
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
            return render(request, 'device/bucketdevice.html', context)

    elif request.method == 'GET':

        yesterday_morning, now = init_datetime_daysago(tz, 1)
        form = bucketDeviceForm(
            initial={
                'start': yesterday_morning,
                'end': now},
            orgs_list=orgs_list
        )
        context = {
                'form': form,
                'console_messages': console_messages,
                'results_display': False,
        }
        return render(request, 'device/bucketdevice.html', context)

    # ------ being here means we have a valid form ------
    start_mark = start.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')
    end_mark = end.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')

    context = {
        'goodrequest': True,
        'form': form,
        'start': start,
        'start_mark': start_mark,
        'end': end,
        'end_mark': end_mark,
        'dev_eui': dev_eui,
        'source_id': source.id,
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

    # It is Query Time!
    start_timer = perf_counter()
    try:
        frames_df = getDeviceFrames(source_id, meas, dev_eui, start_zulu, end_zulu)
    except ValueError as err:
        console_messages.append(F'Cannot getDeviceFrames: {err}')
        error_message = F'Cannot getDeviceFrames: {err}'
        context['results_display'] = False
        context['error_message'] = error_message
        context['console_messages'] = console_messages
        return render(request, 'device/bucketdevice.html', context)

    stop_timer = perf_counter()
    query_time = round(stop_timer - start_timer, 1)
    console_messages.append(F'Source Query Time: {query_time}')

    if frames_df.empty:
        console_messages.append('No data found')
        error_message = 'No data found'
        context['results_display'] = False
        context['error_message'] = error_message
        context['console_messages'] = console_messages
        return render(request, 'device/bucketdevice.html', context)

    # time are UTC

    context['results_display'] = True
    context['frames_received'] = frames_df.shape[0]
    context['frames_first'] = frames_df['time'].min()
    context['frames_last'] = frames_df['time'].max()

    # Now the Gateways
    context['gateway_count'] = frames_df.gateway.nunique()
    if 'gw_latitude' in frames_df.columns and 'gw_longitude' in frames_df.columns:
        gw_loc_df = frames_df[['gateway', 'gw_latitude', 'gw_longitude']].dropna().drop_duplicates(subset=['gateway'])
        gw_loc_df = gw_loc_df.rename(columns={'gw_latitude': 'lat', 'gw_longitude': 'long'})
        gw_loc_df = gw_loc_df.set_index('gateway')
        # these columns no longer needed
        # frames_df = frames_df.rename(columns=['gw_latitude': 'gw_lat, 'gw_longitude': 'gw_long'])
        # gw_loc_df.to_csv(f'{path_out}/{env_name}_gw_locs_{runstamp}.csv')
    else:
        console_messages.append('No gateway locations found')
        gw_loc_df = pd.DataFrame()

    context['gateway_loc_df'] = gw_loc_df

    # get the frames summarized into two tables
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

    # back to frames
    # frames_df['time'] = frames_df['time'].dt.tz_convert(local_tz)
    # ic(frames_df.info())
    frames_out_df = frames_df.copy()
    frames_out_df[['gw_lat', 'gw_long']] = frames_out_df[['gw_lat', 'gw_long']].fillna('')
    context['frames_df'] = frames_out_df

    device_uplinks_df['time'] = device_uplinks_df['time'].dt.tz_convert(local_tz)
    context['device_uplinks_df'] = device_uplinks_df

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

    fig.suptitle(f"DevEUI:{dev_eui}", fontsize=18, fontweight='bold')
    ax1.set_title(f"RF Uplink Performance: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')}")

    ax1.set_ylabel("NR/Misses")
    ax1.set_xlabel("RX Time")
    ax2.set_ylabel("RSSI")

    # time ticks
    myFmt = mdates.HourLocator('%H')
    myFmt = mdates.AutoDateFormatter(myFmt)
    ax1.xaxis.set_major_formatter(myFmt)
    # ax1.set_xticklabels(times,rotation=90)

    # add text
    ax2.text(
            0.5, 0.1,
            F'Uplinks Received: {context["uplinks_received"]}, Missed: {context["uplinks_missed"]}, \
              Success Rate ({round(context["uplinks_pdr"]*100 ,1)}%)',
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

    # plotting

    l2 = ax1.scatter(frames_df['time'], frames_df['snr'], marker='s', color='dodgerblue', s=12)
    l1 = ax2.scatter(everynet_frames_df['time'], everynet_frames_df['rssi'], marker='*', color='#BF40BF', s=30)
    if helium:
        l5 = ax2.scatter(helium_frames_df['time'], helium_frames_df['rssi'], marker='$H$', c='brown', s=30)

    missmarks_df = device_uplinks_df.loc[device_uplinks_df['missed'] > 0]
    l3 = ax1.scatter(missmarks_df['time'], missmarks_df['missed'], marker='^', color='red')

    rejoins_df['mark0'] = 0
    l4 = ax1.scatter(rejoins_df['time'], rejoins_df['mark0'], marker='P', color='fuchsia', s=10**2)

    bigmiss_df = device_uplinks_df.copy().loc[device_uplinks_df['missed'] >= 19]
    bigmiss_df['mark19'] = 19

    ax1.scatter(bigmiss_df['time'], bigmiss_df['mark19'], marker='^', color='red', s=200)

    # remove border lines
    ax1.spines['right'].set_visible(False)
    ax1.spines['top'].set_visible(False)
    ax1.spines['left'].set_visible(False)
    ax1.spines['bottom'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax2.spines['bottom'].set_visible(True)

    # remove ticks
    ax1.tick_params(left=False)
    ax2.tick_params(right=False)
    ax1.tick_params(bottom=False)
    ax2.tick_params(bottom=False)

    # legend
    if helium:
        fig.legend((l1, l5, l2, l3, l4),
                ('RSSI', 'Helium', 'SNR', 'Miss', 'Join'),
                # loc='upper right',
                bbox_to_anchor=(0.94, 1.0),
                fontsize=8,
                title_fontsize=12,
                facecolor='azure',
                fancybox=True,
                framealpha=0.3,
                edgecolor='black'
                )
    else:
        fig.legend((l1, l2, l3, l4),
                ('RSSI', 'SNR', 'Miss', 'Join'),
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

    # ready for return to viewer

    context['console_messages'] = console_messages

    return render(request, 'device/bucketdevice.html', context)
