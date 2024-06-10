from django.urls import path
from .views.geoview import geoView
from .views.geoview2 import geoView2

urlpatterns = [
    path('geoview/', geoView, name='geoview'),
    path(r'geoview/<endnode_id>/<start_mark>/<end_mark>/', geoView, name='geoview_withtimes'),
    path('geoview2/', geoView2, name='geoview2'),
    path(r'geoview2/<endnode_id>/<start_mark>/<end_mark>/', geoView2, name='geoview2_withtimes'),
]
