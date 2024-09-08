from django.urls import path
from .views.views import addEndNode
from .views.bucketdevice import bucketdevice
from .views.packgraph import packgraph

urlpatterns = [
    path('addEndNode/', addEndNode, name='addEndNode'),
    path(r'bucketdevice/<int:source_id>/<str:meas>/<str:dev_eui>/<start_mark>/<end_mark>/',
         bucketdevice, name='bucketdevice_withtimes'),
    path(r'bucketdevice/<int:source_id>/<str:meas>/<str:dev_eui>/', bucketdevice, name='bucketdevice_source'),
    path(r'bucketdevice/', bucketdevice, name='bucketdevice'),
    path(r'packgraph/', packgraph, name='packgraph'),
    path(r'packgraph/<int:endnode_id>/<start_mark>/<end_mark>/', packgraph, name='packgraph_withtimes'),
    path('packgraph/<int:endnode_id>/', packgraph, name='packgraph_withendnode'),
]
