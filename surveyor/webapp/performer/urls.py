from django.urls import path

# from .views import bucketviewgw
from .views.bucketDevicesReport import getTaskInfo

# from .ajax_getBucketDeviceSummary import getBucketDeviceSummary
from .views.bucketDevicesReport import bucketDevicesReport, load_report_groups

# ajax parts
from .ajax_bucketDevicesSummary import bucketDevicesSummary
from .ajax_bucketDevicesMaps import bucketDevicesMaps
from .ajax_bucketDevicesGwInfo import bucketDevicesGwInfo
from .ajax_bucketDevicesDetails import bucketDevicesDetails
from .ajax_bucketDevicesPdr import bucketDevicesPdr

from .views.popout_map import popoutMap


urlpatterns = [

    path('bucketDevicesReport/', bucketDevicesReport, name='bucketDevicesReport'),
    path(
        'bucketDevicesReport/<report_group>/<source_id>/<meas>/<start_mark>/<end_mark>/',
        bucketDevicesReport,
        name='bucketDevicesReport_withTime'
    ),

    path('popoutMap/<task_id>/', popoutMap, name='popoutMap'),
    path('load-report-groups/', load_report_groups, name='load_report_groups'),

    # Task checker
    path('getTaskInfo/', getTaskInfo, name='getTaskInfo'),

    # AJAX Parts
    path('bucketDevicesSummary/', bucketDevicesSummary, name='bucketDevicesSummary'),
    path('bucketDevicesPdr/', bucketDevicesPdr, name='bucketDevicesPdr'),
    path('bucketDevicesMaps/', bucketDevicesMaps, name='bucketDevicesMaps'),
    path('bucketDevicesGwInfo/', bucketDevicesGwInfo, name='bucketDevicesGwInfo'),
    # path('bucketDevicesMapTwo/', bucketDevicesMapTwo, name='bucketDevicesMapTwo'),
    path('bucketDevicesDetails/', bucketDevicesDetails, name='BucketDevicesDetails'),

]
