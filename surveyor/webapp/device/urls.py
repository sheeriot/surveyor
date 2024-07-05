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
    path(r'packgraph2/<int:endnode_id>/<start_mark>/<end_mark>/', packgraph2, name='packgraph2_withtimes'),
    path('packgraph2/<int:endnode_id>/', packgraph2, name='packgraph2_withendnode'),

]
