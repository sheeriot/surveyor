from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
# from django.template.loader import render_to_string
from django.utils import timezone
from celery.result import AsyncResult

import dateutil.parser
import dateutil.tz

from surveyor.settings import TIME_ZONE
from surveyor.utils import init_datetime_daysago
from accounts.models import Person
from device.models import InfluxSource
from .task_createBucketDevicesReport import create_bucketDevicesReport

from .form_bucketDevicesReport import bucketDevicesForm

# from icecream import ic


@login_required
def bucketDevicesReport(request, **kwargs):
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

        form = bucketDevicesForm(request.GET, orgs_list=orgs_list)

        if form.is_valid():
            start = form.cleaned_data["start"]
            start_zulu = start.astimezone(zulu_tz)
            end = form.cleaned_data["end"]
            end_zulu = end.astimezone(zulu_tz)
            source = form.cleaned_data["source"]
            meas = form.cleaned_data["meas"]
            center_latitude = form.cleaned_data["center_latitude"]
            center_longitude = form.cleaned_data["center_longitude"]
            radius_km = form.cleaned_data["radius_km"]
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
            return render(request, 'performer/bucketdevices_report.html', context)

    elif request.method == 'GET' and kwargs:

        form = bucketDevicesForm(request.GET, orgs_list=orgs_list)
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

        form = bucketDevicesForm(
            {
             'start': start,
             'end': end,
             'source': source_id,
             'meas': meas,
             'center_latitude': None,
             'center_longitude': None,
             'radius_km': None
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
            center_latitude = form.cleaned_data["center_latitude"]
            center_longitude = form.cleaned_data["center_longitude"]
            radius_km = form.cleaned_data["radius_km"]
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
            return render(request, 'performer/bucketdevices_report.html', context)

    elif request.method == 'GET':
        # a GET with no KWARGS, let's set some defaults and return the form
        start_morning, now = init_datetime_daysago(tz, 3)
        # start, end = init_datetime_daysago(tz, days_ago=7)
        form = bucketDevicesForm(initial={'start': start_morning, 'end': now}, orgs_list=orgs_list)
        console_messages.append('GET with no-args - using defaults')
        context = {
            'form': form,
            'console_messages': console_messages,
            'results_display': False,
        }
        return render(request, 'performer/bucketdevices_report.html', context)

    # Form Processing Requested

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

    # if center_latitude is not None and center_longitude is not None:
    #     context['center_latitude'] = center_latitude
    #     context['center_longitude'] = center_longitude
    #     context['radius_km'] = radius_km
    # else:
    #     center_latitude = None
    #     center_longitude = None
    #     radius_km = None

    async_result = create_bucketDevicesReport.delay(
        source.id, meas, start_mark, end_mark,
        center=(center_latitude, center_longitude),
        rings=radius_km, requester=person.username)

    task_id = async_result.task_id
    console_messages.append(F'Task ID: {task_id}')
    context['task_id'] = task_id

    context['results_display'] = False
    context['console_messages'] = console_messages
    return render(request, 'performer/bucketdevices_report.html', context)


@login_required
def getTaskInfo(request):
    task_id = request.GET.get('task_id', None)
    if task_id is not None:
        task = AsyncResult(task_id)
        data = {
            'state': task.state,
            # 'result': task.result,
        }
        return JsonResponse(data)
    else:
        return HttpResponse('No job id given.')
