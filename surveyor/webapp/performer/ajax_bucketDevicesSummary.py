from django.contrib.auth.decorators import login_required

from django.http import HttpResponse

from django.template.loader import render_to_string

from celery.result import AsyncResult
import redis
import json

import dateutil.parser
import dateutil.tz

# from icecream import ic


@login_required
def bucketDevicesSummary(request):

    task_id = request.GET.get('task_id', None)

    # if timezone.get_current_timezone():
    #     tz = str(timezone.get_current_timezone())
    # else:
    #     tz = TIME_ZONE
    zulu_tz = dateutil.tz.gettz('UTC')
    # local_tz = dateutil.tz.gettz(tz)

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

        context = {
            'totals_dict': totals_dict,
        }
        rendered = render_to_string('performer/bucketDevicesSummary.html', context)
        return HttpResponse(rendered)

    else:
        return HttpResponse('No job id given.')
