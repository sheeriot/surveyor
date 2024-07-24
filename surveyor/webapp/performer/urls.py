from django.urls import path

# from .views import bucketviewgw
from .view_bucketDevicesReport import getTaskInfo

# from .ajax_getBucketDeviceSummary import getBucketDeviceSummary
from .view_bucketDevicesReport import bucketDevicesReport
# ajax parts
from .ajax_bucketDevicesSummary import bucketDevicesSummary
from .ajax_bucketDevicesMaps import bucketDevicesMaps
from .ajax_bucketDevicesGwInfo import bucketDevicesGwInfo
from .ajax_bucketDevicesDetails import bucketDevicesDetails
from .ajax_bucketDevicesPdr import bucketDevicesPdr

from .views.popout_map import popoutMap

from .views.bucketDevicesReport2 import bucketDevicesReport2, load_report_groups

urlpatterns = [
    # Task checker
    path('getTaskInfo/', getTaskInfo, name='getTaskInfo'),

    path('bucketDevicesReport/', bucketDevicesReport, name='bucketDevicesReport'),
    path(
        'bucketDevicesReport/<source_id>/<meas>/<start_mark>/<end_mark>/',
        bucketDevicesReport,
        name='bucketDevicesReport_withTime'
    ),
    path('popoutMap/<task_id>/', popoutMap, name='popoutMap'),

    # AJAX Parts
    path('bucketDevicesSummary/', bucketDevicesSummary, name='bucketDevicesSummary'),
    path('bucketDevicesPdr/', bucketDevicesPdr, name='bucketDevicesPdr'),
    path('bucketDevicesMaps/', bucketDevicesMaps, name='bucketDevicesMaps'),
    path('bucketDevicesGwInfo/', bucketDevicesGwInfo, name='bucketDevicesGwInfo'),
    # path('bucketDevicesMapTwo/', bucketDevicesMapTwo, name='bucketDevicesMapTwo'),
    path('bucketDevicesDetails/', bucketDevicesDetails, name='BucketDevicesDetails'),

    # Beta
    path('bucketDevicesReport2/', bucketDevicesReport2, name='bucketDevicesReport2'),
    path(
        'bucketDevicesReport2/<report_group>/<source_id>/<meas>/<start_mark>/<end_mark>/',
        bucketDevicesReport2,
        name='bucketDevicesReport2_withTime'
    ),
    path('load-report-groups/', load_report_groups, name='load_report_groups'),
]
