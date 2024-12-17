from django.urls import path
from .views import *

urlpatterns = [
    path('convert-tiff/', convert_tiff, name='convert_tiff')
]
