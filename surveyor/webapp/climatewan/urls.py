from django.urls import path, re_path
from .views import heatIndex

urlpatterns = [
    path(r'heatIndex/', heatIndex, name='heatIndex'),
    path(r'heatIndex/<int:endnode_id>/<str:start_mark>/<str:end_mark>/', heatIndex, name='heat_withtimes'),
    re_path(r'^heatIndex/(?P<endnodes>[0-9]+)/(?P<start>[\w-]+)/(?P<end>[\w-]+)/(?P<submit>[\w-]+)$',
            heatIndex,
            name='heat_repath')
    ]
