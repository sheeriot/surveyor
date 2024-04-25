from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string

# from icecream import ic


@login_required
def bucketDevicesMaps(request):
    # pass the TaskID along to the Pop-out Map.
    task_id = request.GET.get('task_id', None)

    if task_id is None:
        return HttpResponse('No Task_ID was given.')

    context = {
        'task_id': task_id,
    }

    context["task_id"] = task_id

    rendered = render_to_string('performer/bucketDevicesMaps.html', context)
    return HttpResponse(rendered)
