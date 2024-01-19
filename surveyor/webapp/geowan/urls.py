from django.urls import path
from .views.geoview import geoView

urlpatterns = [
    path('geoview/', geoView, name='geoview'),
    path(r'geoview/<endnode_id>/<start_mark>/<end_mark>/', geoView, name='geoview_withtimes'),
]
