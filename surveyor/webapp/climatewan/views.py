from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

import dateutil.parser
import dateutil.tz

# from icecream import ic

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib as mpl

from surveyor.settings import TIME_ZONE
from surveyor.utils import getGraph, graphSetUp, init_datetime

from .climatefun import getInfluxClimateData

from device.models import EndNode
from accounts.models import Person
from packTrack.form_endnode import endNodeSelect


@login_required
def heatIndex(request, **kwargs):
    username = request.user
    person = Person.objects.get(username=username)
    orgs_list = person.orgs_list()

    if timezone.get_current_timezone():
        tz = str(timezone.get_current_timezone())
    else:
        tz = TIME_ZONE
    zulu_tz = dateutil.tz.gettz('UTC')
    local_tz = dateutil.tz.gettz(tz)

    console_messages = []
    console_messages.append(F'Local Timezone: {tz}')

    if request.method == 'GET' and 'submit' in request.GET:
        form = endNodeSelect(request.GET, orgs_list=orgs_list)
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
            return render(request, 'climatewan/heatIndex.html', context)

    elif request.method == 'GET' and kwargs:
        if 'start_mark' in kwargs:
            start_mark = kwargs.pop('start_mark')
            start_zulu = dateutil.parser.parse(start_mark).replace(tzinfo=zulu_tz)
            start = start_zulu.astimezone(local_tz)
        if 'end_mark' in kwargs:
            end_mark = kwargs.pop('end_mark')
            end_zulu = dateutil.parser.parse(end_mark).replace(tzinfo=zulu_tz)
            end = end_zulu.astimezone(local_tz)
        if 'endnode_id' in kwargs:
            endnode_id = kwargs.pop('endnode_id')
            endnode = EndNode.objects.get(pk=endnode_id)

        form = endNodeSelect({
            "endnode": endnode_id,
            "start": start,
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
            return render(request, 'climatewan/heatIndex.html', context)

    elif request.method == 'GET':

        yesterday_morning, now = init_datetime(tz)
        form = endNodeSelect(
            initial={
                'start': yesterday_morning,
                'end': now},
            orgs_list=orgs_list
        )
        start = dateutil.parser.parse(yesterday_morning).replace(tzinfo=local_tz)
        start_mark = start.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')
        end = dateutil.parser.parse(now).replace(tzinfo=local_tz)
        end_mark = end.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')
        context = {
            'form': form,
            'start_mark': start_mark,
            'end_mark': end_mark,
            'console_messages': console_messages,
            'results_display': False,
        }
        return render(request, 'climatewan/heatIndex.html', context)

# ------ being here means we have a valid form ------

    start_mark = start.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')
    end_mark = end.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')

    context = {
        'form': form,
        'start': start,
        'start_mark': start_mark,
        'end': end,
        'end_mark': end_mark,
        'endnode': endnode,
        'endnode_id': endnode_id,
        'source': source,
        'source_id': source_id,
        'meas': meas,
    }

    # get the data from influx, now with error feedback as ValueError
    try:
        frames_df = getInfluxClimateData(source.id, meas,
                                         dev_eui, start_zulu, end_zulu)
    except ValueError as err:
        console_messages.append(F'Cannot getInfluxClimateData: {err}')
        error_message = F'Cannot get Climate data: {err}'
        context['error_message'] = error_message
        context['console_messages'] = console_messages
        return render(request, 'climatewan/heatIndex.html', context)

    # if the dataframe is empty, return to the form with a message
    if frames_df.empty:
        context["results_display"] = False
        error_message = "No results: Dataframe Empty"
        context['error_message'] = error_message
        console_messages.append(error_message)
        context["console_messages"] = console_messages
        return render(request, 'climatewan/heatIndex.html', context)

    context['results_display'] = True
    context['frames_received'] = frames_df.shape[0]
    context['frames_first'] = frames_df['time'].min()
    context['frames_last'] = frames_df['time'].max()

    # set battery metric and a new battery column; battery_level or battery_voltage
    if "battery_level" in frames_df.columns:
        battery_metric = "level"
        frames_df['battery'] = frames_df['battery_level']
        frames_df = frames_df.drop(columns=['battery_level'])
        battery_last = frames_df['battery'].iloc[-1]
        battery_last = f'{battery_last}%'

    elif "battery_voltage" in frames_df.columns:
        battery_metric = "voltage"
        frames_df['battery'] = frames_df['battery_voltage'].round(2)
        frames_df = frames_df.drop(columns=['battery_voltage'])
        battery_last = frames_df['battery'].iloc[-1]
        battery_last = f'{battery_last}v'
    else:
        battery_metric = "none"
        battery_last = '--'

    context["battery_metric"] = battery_metric
    context["battery_last"] = battery_last

    # set up graph
    mpl.rcParams['timezone'] = tz
    graphSetUp(width=10, height=6)
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    fig.patch.set_facecolor('#ECECEC')
    ax1.set_facecolor('#ECECEC')

    fig.suptitle(f"{endnode.name}({endnode.dev_eui})", fontsize=18, fontweight='bold')
    ax1.set_title(f"Climate Data: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%Y-%m-%d %H:%M')}")

    ax2.set_ylabel("Temperature/Humidity")
    ax1.set_xlabel("Time")

    # Setup Y-axis for Battery Metric, and plot
    if battery_metric == "voltage":
        ax1.set_ylabel("Battery Voltage")
        ax1.set_ylim([0, 6])
    elif battery_metric == "level":
        ax1.set_ylabel("Battery Level")
        ax1.set_ylim([0, 120])

    battery_df = frames_df[['time', 'battery']].copy().dropna()
    ax1.plot(battery_df['time'], battery_df['battery'], color="green", label="Battery")

    ax1.set_xlim(start, end)
    ax1.grid(False)
    # enable X-Axis grid
    ax1.xaxis.grid(True)

    # time ticks
    myFmt = mdates.HourLocator('%H')
    myFmt = mdates.AutoDateFormatter(myFmt)
    ax1.xaxis.set_major_formatter(myFmt)
    # ax1.set_xticklabels(times)

    # AX2 - Y axis limits
    ax2.set_ylim([0, 120])

    # AX2 plotting - or fill the blank columns with None
    if 'temperature' in frames_df.columns:
        temperature_df = frames_df[['time', 'temperature']].copy().dropna()
        ax2.plot(temperature_df['time'], temperature_df['temperature'], color="red", label="Temperature")

    if 'humidity' in frames_df.columns:
        humidity_df = frames_df[['time', 'humidity']].copy().dropna()
        ax2.plot(humidity_df['time'], humidity_df['humidity'], color="blue", label="Humidity")

    fig.legend()

    ax1.spines['right'].set_visible(False)
    ax1.spines['top'].set_visible(False)
    ax1.spines['left'].set_visible(False)
    ax1.spines['bottom'].set_visible(True)
    ax2.spines['right'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax2.spines['bottom'].set_visible(False)

    # remove ticks
    ax1.tick_params(left=False)
    ax2.tick_params(right=False)
    ax1.tick_params(bottom=False)
    ax2.tick_params(bottom=False)

    # create grid
    plt.grid(True)
    ax1.xaxis.grid(True)

    # create graph and pass it to the context
    graph = getGraph()
    context["graph"] = graph

    # format battery with unit for dsiplay
    if battery_metric == "voltage":
        frames_df['battery'] = frames_df['battery'].astype(str) + 'v'
    elif battery_metric == "level":
        frames_df['battery'] = frames_df['battery'].astype(str) + '%'

    # convert time to local timezone
    frames_df['time'] = frames_df['time'].dt.tz_convert(tz)
    context['frames_df'] = frames_df

    context["console_messages"] = console_messages
    return render(request, 'climatewan/heatIndex.html', context)
