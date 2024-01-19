from django.urls import path
# from .views import packGraph
from .views import packGraph

urlpatterns = [
    path('packGraph/', packGraph, name='packGraph'),
    path(r'packGraph/<endnode>/<start>/<end>/<submit>', packGraph, name='packGraph'),
    path(r'packGraph/<int:endnode_id>/<start_mark>/<end_mark>/', packGraph, name='packgraph_withtimes'),
]
