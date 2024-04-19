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


urlpatterns = [
    # Task checker
    path('getTaskInfo/', getTaskInfo, name='getTaskInfo'),

    path('bucketDevicesReport/', bucketDevicesReport, name='bucketDevicesReport'),
    path(
        'bucketDevicesReport/<source_id>/<meas>/<start_mark>/<end_mark>/',
        bucketDevicesReport,
        name='bucketDevicesReport_withTime'
    ),

    # AJAX Parts
    path('bucketDevicesSummary/', bucketDevicesSummary, name='bucketDevicesSummary'),
    path('bucketDevicesPdr/', bucketDevicesPdr, name='bucketDevicesPdr'),
    path('bucketDevicesMaps/', bucketDevicesMaps, name='bucketDevicesMaps'),
    path('bucketDevicesGwInfo/', bucketDevicesGwInfo, name='bucketDevicesGwInfo'),
    # path('bucketDevicesMapTwo/', bucketDevicesMapTwo, name='bucketDevicesMapTwo'),
    path('bucketDevicesDetails/', bucketDevicesDetails, name='BucketDevicesDetails'),
]
