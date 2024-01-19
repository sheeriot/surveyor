from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

# from icecream import ic
from time import perf_counter
import dateutil.parser
import dateutil.tz

from accounts.models import Person
from device.models import InfluxSource
from surveyor.utils import getGraph, init_datetime_daysago
from surveyor.settings import TIME_ZONE

from .forms import bucketviewGwForm
from .subbands import get_subbands
from .getbucket import getBucketData
from .getstats import getGatewayStats

import matplotlib.pyplot as plt

import seaborn as sns
# import folium

import warnings
from .forms import bucketDevicesDelayForm
warnings.simplefilter(action='ignore', category=FutureWarning)


@login_required
def bucketviewgw(request, source_id='', **kwargs):
    # get the Person to scope endnodes and orgs
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

    # find selected bucket, if none than assumed to be first
    if request.method == 'GET' and 'submit' in request.GET:

        form = bucketviewGwForm(request.GET, orgs_list=orgs_list)

        if form.is_valid():
            start = form.cleaned_data["start"]
            start_zulu = start.astimezone(zulu_tz)
            end = form.cleaned_data["end"]
            end_zulu = end.astimezone(zulu_tz)
            source = form.cleaned_data["source"]
            source_id = source.id
            meas = form.cleaned_data["meas"]
        else:
            console_messages.append(F'Submitted Form Invalid: {form.errors}')
            console_messages.append(F'Form Data: {form.data}')
            console_messages.append(F'Form Cleaned Data: {form.cleaned_data}')
            console_messages.append(F'Kwargs: {kwargs}')
            context = {
                'form': form,
                'console_messages': console_messages,
                'results_display': False,
                'error_message': form.errors
                }
            return render(request, 'device/bucketviewgw.html', context)

    elif request.method == 'GET' and kwargs:
        if 'start_mark' in kwargs:
            start_mark = kwargs.pop('start_mark')
            start_zulu = dateutil.parser.parse(start_mark).replace(tzinfo=zulu_tz)
            start = start_zulu.astimezone(local_tz)
        if 'end_mark' in kwargs:
            end_mark = kwargs.pop('end_mark')
            end_zulu = dateutil.parser.parse(end_mark).replace(tzinfo=zulu_tz)
            end = end_zulu.astimezone(local_tz)
        if 'source_id' in kwargs:
            source_id = kwargs.pop('source_id')
            source = InfluxSource.objects.get(pk=source_id)
        if 'meas' in kwargs:
            meas = kwargs.pop('meas')

        form = bucketDevicesDelayForm(
            {
                'start': start,
                'end': end,
                'source': source,
                'meas': meas
            },
            orgs_list=orgs_list
        )
        if form.is_valid():
            start = form.cleaned_data["start"]
            start_zulu = start.astimezone(zulu_tz)
            end = form.cleaned_data["end"]
            end_zulu = end.astimezone(zulu_tz)
            source = form.cleaned_data["source"]
            meas = form.cleaned_data["meas"]
        else:
            console_messages.append(F'Submitted Form Invalid: {form.errors}')
            console_messages.append(F'Form Data: {form.data}')
            console_messages.append(F'Form Cleaned Data: {form.cleaned_data}')
            console_messages.append(F'Kwargs: {kwargs}')
            context = {
                'form': form,
                'console_messages': console_messages,
                'results_display': False,
                'error_message': form.errors
                }
        return render(request, 'performer/bucketviewgw.html', context)

    elif request.method == 'GET':
        # a GET with no KWARGS, let's set some defaults and return the form
        start_morning, now = init_datetime_daysago(tz, 3)
        # start, end = init_datetime_daysago(tz, days_ago=7)
        form = bucketviewGwForm(initial={'start': start_morning, 'end': now}, orgs_list=orgs_list)
        console_messages.append('GET with no-args - using defaults')
        context = {
            'form': form,
            'console_messages': console_messages,
            'results_display': False,
        }
        return render(request, 'performer/bucketviewgw.html', context)

    # start processing

    start_mark = start.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')
    end_mark = end.astimezone(zulu_tz).strftime('%Y%m%dT%H%MZ')

    # Start building the context
    context = {
        'form': form,
        'source_name': source.name,
        'source_id': source.id,
        'meas': meas,
        'start': start,
        'end': end,
        'start_mark': start_mark,
        'end_mark': end_mark,
    }

    # InfluxDB Query with timer output
    start_timer = perf_counter()

    query_results, pdf = getBucketData(source_id, meas, start_mark, end_mark)
    stop_timer = perf_counter()
    influx_query_time = stop_timer - start_timer
    console_messages.append(F'InfluxDB Query Time: {influx_query_time}')

    record_count = pdf.shape[0]
    pdf_size = pdf.memory_usage(deep=True).sum()

    console_messages.append(F'Records:{record_count},Size={pdf_size}')
    # print(F'Results - Type:{type(pdf)},Records:{record_count},Size={pdf_size}')
    context['results_display'] = True if record_count > 0 else False

    # If the results is a List of Dataframes, go fix the source data (or query?)
    if type(pdf) is list:
        console_messages.append(F'Influx Result is a List! Must be a dataframe. Fix data Source. length:{len(pdf)}')
        return render(request, 'performer/bucketviewgw.html', context)

    # begin Gateway View

    # Create gw_loc_df
    gw_loc_df = pdf[['gateway', 'gw_latitude', 'gw_longitude']].drop_duplicates().dropna().reset_index(drop=True)
    context['gw_loc_df'] = gw_loc_df

    # Create a Gateway Summary Dataframe
    gateway_summ_df = getGatewayStats(pdf)
    context['gateway_summ_df'] = gateway_summ_df

    # Put a time range on the plot for reference
    time_first = pdf['_time'].min().strftime("%Y-%m-%d %H:%M:%S")
    context['time_first'] = time_first
    time_last = pdf['_time'].max().strftime("%Y-%m-%d %H:%M:%S")
    context['time_last'] = time_last

    # add Sub-bands table, add to the pdf
    subbands_df = get_subbands()
    pdf = pdf.join(subbands_df, on='frequency', how='left')

    # now the gateway graphs

    sns.set_style("whitegrid")

    fig, axes = plt.subplots(3, figsize=(10, 8))
    axes = axes.ravel()

    sns.histplot(data=pdf, x="subband", hue="gateway", multiple="dodge", discrete=True, ax=axes[0])
    sns.move_legend(axes[0], "lower right", ncol=1, fontsize='x-small', title_fontsize='small', framealpha=0.5)
    axes[0].set(xlabel=None)

    sns.boxplot(data=pdf, x="subband", y="rssi", hue="gateway", ax=axes[1])
    sns.move_legend(axes[1], "lower right", ncol=1, fontsize='x-small', title_fontsize='small', framealpha=0.5)
    axes[1].set(xlabel=None)

    fig.suptitle(f'{source} - RF Performance Summary\nFirst: {time_first}\nLast: {time_last}',
                 fontsize=10, fontweight='bold')

    # does this have any real chance of working
    # graph = getGraph()
    # context["graph"] = graph

    # pack the plot into the context
    graph = getGraph()
    context["graph"] = graph

    # context['uplink_list_dict'] = uplinks_list_dict

    # pass on context and return template
    context['console_messages'] = console_messages

    return render(request, 'performer/bucketviewgw.html', context)
