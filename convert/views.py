from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import UploadedFile
import geopandas as gpd
from PIL import Image
import rasterio
import numpy as np
import io
import base64
from rasterio.plot import reshape_as_image
from rasterio.warp import transform_bounds
from zipfile import ZipFile
import tempfile


@csrf_exempt
def convert_tiff(request):
    """Convert a TIFF file to PNG with transparent background."""
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            uploaded_file: UploadedFile = request.FILES['file']

            with rasterio.open(uploaded_file) as src:
                bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds) if src.crs != "EPSG:4326" else src.bounds
                data = src.read(out_shape=(src.count, src.height // 10, src.width // 10))
                data = reshape_as_image(data[:3])
                data_normalized = ((data - data.min()) / (data.max() - data.min()) * 255).astype(np.uint8)

                img = Image.fromarray(data_normalized).convert("RGBA")
                datas = img.getdata()
                new_data = [(0, 0, 0, 0) if item[:3] < (10, 10, 10) else item for item in datas]
                img.putdata(new_data)

                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

                return JsonResponse({
                    'base64_image': f"data:image/png;base64,{img_base64}",
                    'bounds': [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]
                })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def convert_shapefile(request):
    """Convert uploaded Shapefile to GeoJSON."""
    if request.method == 'POST' and request.FILES.getlist('files'):
        try:
            uploaded_files = {file.name: file for file in request.FILES.getlist('files')}
            with tempfile.TemporaryDirectory() as temp_dir:
                for file_name, uploaded_file in uploaded_files.items():
                    with open(f"{temp_dir}/{file_name}", 'wb') as temp_file:
                        temp_file.write(uploaded_file.read())

                gdf = gpd.read_file(temp_dir)
                geojson = gdf.to_json()

            return JsonResponse({'geojson': geojson})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def get_shapefile_bounds(request):
    """Return the bounds of an uploaded shapefile."""
    if request.method == 'POST' and request.FILES.getlist('files'):
        try:
            uploaded_files = {file.name: file for file in request.FILES.getlist('files')}
            with tempfile.TemporaryDirectory() as temp_dir:
                for file_name, uploaded_file in uploaded_files.items():
                    with open(f"{temp_dir}/{file_name}", 'wb') as temp_file:
                        temp_file.write(uploaded_file.read())

                gdf = gpd.read_file(temp_dir)
                bounds = gdf.total_bounds.tolist()

            return JsonResponse({'bounds': bounds})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)
