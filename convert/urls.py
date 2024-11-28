from django.urls import path
from .views import *

urlpatterns = [
    path('convert-tiff/', convert_tiff, name='convert_tiff'),
    path('convert-shapefile/', convert_shapefile, name='convert_shapefile'),
    path('get-shapefile-bounds/', get_shapefile_bounds, name='get_shapefile_bounds'),
    path('convert-tiff/', ConvertTiffAPIView.as_view(), name='convert-tiff'),
]
