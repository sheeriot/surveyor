from django.urls import path
from .views import addEndNode, bucketdevice


urlpatterns = [
    path('addEndNode/', addEndNode, name='addEndNode'),
    path(r'bucketdevice/<int:source_id>/<str:meas>/<str:dev_eui>/<start_mark>/<end_mark>/',
         bucketdevice, name='bucketdevice_withtimes'),
    path(r'bucketdevice/<int:source_id>/<str:meas>/<str:dev_eui>/', bucketdevice, name='bucketdevice_source'),
    path(r'bucketdevice/', bucketdevice, name='bucketdevice'),
]
