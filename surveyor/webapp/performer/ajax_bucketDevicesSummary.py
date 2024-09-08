from django.contrib.auth.decorators import login_required

from django.http import HttpResponse

from django.template.loader import render_to_string

from celery.result import AsyncResult
import redis
import json
import pandas as pd

import dateutil.parser
import dateutil.tz

# from device.models import BucketDevice
# from icecream import ic


@login_required
def bucketDevicesSummary(request):

    task_id = request.GET.get('task_id', None)
    zulu_tz = dateutil.tz.gettz('UTC')

    if task_id is not None:
        task = AsyncResult(task_id)
        source_id, meas, start_mark, end_mark = eval(task.args)

        report_status, totals_dict = task.result

        if task.state == 'SUCCESS':

            if report_status.lower().startswith(("failed", "empty")):
                return HttpResponse(F'Report Summary: {report_status}')

            # Connect to Redis to get summary table
            redis_client = redis.Redis(host='redis', port=6379, db=0)
            # Get the JSON string from Redis
            totals_dict_json = redis_client.get(f'{task_id}:totals_dict')

            # Convert the JSON string back to a dictionary
            if totals_dict_json is not None:
                totals_dict = json.loads(totals_dict_json)
                totals_dict['frame_first'] = dateutil.parser.parse(totals_dict['frame_first']).replace(tzinfo=zulu_tz)
                totals_dict['frame_last'] = dateutil.parser.parse(totals_dict['frame_last']).replace(tzinfo=zulu_tz)
            else:
                totals_dict = None
        else:
            totals_dict = None

        # reconstitute the device_uplinks_df
        device_uplinks_json = redis_client.get(f'{task_id}:device_uplinks_df')
        device_uplinks_dict = json.loads(device_uplinks_json)
        device_uplinks_df = pd.DataFrame(device_uplinks_dict)

        # reconstitute the device_locs_df
        device_loc_json = redis_client.get(f'{task_id}:device_loc_df')
        device_loc_dict = json.loads(device_loc_json)
        device_loc_df = pd.DataFrame(device_loc_dict)

        devices_seen = list(device_uplinks_df['dev_eui'])
        if device_loc_df.empty:
            devices_withloc = []
            devices_missing = []
        else:
            devices_withloc = list(device_loc_df['dev_eui'])
            devices_missing = set(devices_withloc) - set(devices_seen)
            # devices_missing_df = [device_loc_df[device_loc_df['dev_eui'].isin(devices_missing)]]
        devices_noloc = set(devices_seen) - set(devices_withloc)

        device_counts = {
            'withloc': len(devices_withloc),
            'seen': len(devices_seen),
            'missing': len(devices_missing),
            'noloc': len(devices_noloc)
        }

        context = {
            'totals_dict': totals_dict,
            'device_counts': device_counts
        }
        
        if 'downlinks_total' in totals_dict:
            context['downlinks'] = True

        rendered = render_to_string('performer/bucketDevicesSummary.html', context)
        return HttpResponse(rendered)

    else:
        return HttpResponse('No job id given.')
