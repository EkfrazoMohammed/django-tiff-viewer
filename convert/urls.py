from django.urls import path
from .views import convert_tiff, convert_shapefile, get_shapefile_bounds

urlpatterns = [
    path('convert-tiff/', convert_tiff, name='convert_tiff'),
    path('convert-shapefile/', convert_shapefile, name='convert_shapefile'),
    path('get-shapefile-bounds/', get_shapefile_bounds, name='get_shapefile_bounds'),
]
