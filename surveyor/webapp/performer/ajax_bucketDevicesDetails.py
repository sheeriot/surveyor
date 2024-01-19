from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from celery.result import AsyncResult

from surveyor.settings import TIME_ZONE

import dateutil.parser
import dateutil.tz

# from icecream import ic
import json
import pandas as pd
import redis


@login_required
def bucketDevicesDetails(request):
    task_id = request.GET.get('task_id', None)
    if task_id is None:
        return HttpResponse("No task_id provided")

    # setup timezone stuff
    if timezone.get_current_timezone():
        tz = str(timezone.get_current_timezone())
    else:
        tz = TIME_ZONE
    zulu_tz = dateutil.tz.gettz('UTC')
    local_tz = dateutil.tz.gettz(tz)

    # fetch the task AsyncResult
    task = AsyncResult(task_id)
    report_status, totals_dict = task.result
    source_id, meas, start_mark, end_mark = eval(task.args)

    # start_zulu = dateutil.parser.parse(start_mark).replace(tzinfo=zulu_tz)
    # end_zulu = dateutil.parser.parse(end_mark).replace(tzinfo=zulu_tz)

    if task.state != 'SUCCESS':
        return HttpResponse(F'TASK STATE: {task.state}')

    if report_status.lower().startswith(("failed", "empty")):
        return HttpResponse(F'NO DETAILS: {report_status}')

    # create the redis client
    redis_client = redis.Redis(host='redis', port=6379, db=0)

    # reconstitute the device_uplinks_df
    device_uplinks_json = redis_client.get(f'{task_id}:device_uplinks_df')
    device_uplinks_dict = json.loads(device_uplinks_json)
    device_uplinks_df = pd.DataFrame(device_uplinks_dict)

    # fix the timestamps from string
    device_uplinks_df['frame_first'] = pd.to_datetime(device_uplinks_df['frame_first'],
                                                      unit='ms').dt.tz_localize(zulu_tz)
    device_uplinks_df['frame_first'] = device_uplinks_df['frame_first'].dt.tz_convert(local_tz)
    device_uplinks_df['frame_last'] = pd.to_datetime(device_uplinks_df['frame_last'],
                                                     unit='ms').dt.tz_localize(zulu_tz)
    device_uplinks_df['frame_last'] = device_uplinks_df['frame_last'].dt.tz_convert(local_tz)

    # now the device/gateway tables
    device_gw_json = redis_client.get(f'{task_id}:device_gw_df')
    device_gw_dict = json.loads(device_gw_json)
    device_gw_df = pd.DataFrame(device_gw_dict)

    # rename some columns for tighter tables
    device_uplinks_df = device_uplinks_df.rename(
        columns={
            'uplinks_pdr': 'pdr',
            'uplinks_total': 'total',
            'uplinks_received': 'received',
            'uplinks_missed': 'missed',
            'frames_received': 'frames',
            'join_seqs': 'joins',
        }
    )
    device_gw_df = device_gw_df.rename(
        columns={
            'frame_count': 'received',
            'uplinks_total': 'uplinks',
        }
    )

    context = {
        'source_id': source_id,
        'meas': meas,
        'start_mark': start_mark,
        'end_mark': end_mark,
        'device_uplinks_df': device_uplinks_df,
        'device_gw_df': device_gw_df,
    }
    report_details_html = render_to_string('performer/bucketDevicesDetails.html', context)
    return HttpResponse(report_details_html)
