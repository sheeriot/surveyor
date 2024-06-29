from django.urls import path
from .views.views import addEndNode, bucketdevice
from .views.packgraph2 import packgraph2

urlpatterns = [
    path('addEndNode/', addEndNode, name='addEndNode'),
    path(r'bucketdevice/<int:source_id>/<str:meas>/<str:dev_eui>/<start_mark>/<end_mark>/',
         bucketdevice, name='bucketdevice_withtimes'),
    path(r'bucketdevice/<int:source_id>/<str:meas>/<str:dev_eui>/', bucketdevice, name='bucketdevice_source'),
    path(r'bucketdevice/', bucketdevice, name='bucketdevice'),
    path(r'packgraph2/', packgraph2, name='packgraph2'),
]
