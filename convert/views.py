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
    if request.method == "POST" and request.FILES.get("file"):
        # try:
        #     uploaded_file: UploadedFile = request.FILES['file']

        #     with rasterio.open(uploaded_file) as src:
        #         bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds) if src.crs != "EPSG:4326" else src.bounds
        #         data = src.read(out_shape=(src.count, src.height // 10, src.width // 10))
        #         data = reshape_as_image(data[:3])
        #         data_normalized = ((data - data.min()) / (data.max() - data.min()) * 255).astype(np.uint8)

        #         img = Image.fromarray(data_normalized).convert("RGBA")
        #         datas = img.getdata()
        #         new_data = [(0, 0, 0, 0) if item[:3] < (10, 10, 10) else item for item in datas]
        #         img.putdata(new_data)

        #         img_byte_arr = io.BytesIO()
        #         img.save(img_byte_arr, format='PNG')
        #         img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        #         return JsonResponse({
        #             'base64_image': f"data:image/png;base64,{img_base64}",
        #             'bounds': [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]
        #         })
        # except Exception as e:
        #     return JsonResponse({'error': str(e)}, status=500)

        # HD clarity
        try:
            # Get the uploaded file
            uploaded_file = request.FILES.get("file")
            if not uploaded_file:
                return JsonResponse({"error": "No file uploaded"}, status=400)

            # Read the file into memory
            contents = uploaded_file.read()

            # Open the TIFF file from the uploaded bytes
            with rasterio.open(io.BytesIO(contents)) as src:
                # Transform bounds to WGS84 if necessary
                bounds = (
                    transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                    if src.crs != "EPSG:4326"
                    else src.bounds
                )

                # Read the image data
                data = src.read()

                # Handle floating-point data: normalize to uint8
                if np.issubdtype(data.dtype, np.floating):
                    data = np.nan_to_num(data)  # Replace NaN with 0
                    data = (
                        (data - data.min()) / (data.max() - data.min()) * 255
                    ).astype(np.uint8)

                # If the TIFF has more than 3 bands, limit to the first three (RGB)
                if data.shape[0] > 3:
                    data = data[:3]

                # Convert the normalized array to an RGB image
                img = Image.fromarray(reshape_as_image(data))

                # Add an alpha channel for transparency
                img = img.convert("RGBA")

                # Replace black pixels with transparent ones (customizable threshold)
                datas = img.getdata()
                new_data = [
                    (0, 0, 0, 0) if max(item[:3]) < 10 else item for item in datas
                ]
                img.putdata(new_data)

                # Save the image to a byte array with high-quality compression
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="PNG", optimize=True)

                # Convert image to base64 string
                img_byte_arr.seek(0)
                img_base64 = base64.b64encode(img_byte_arr.read()).decode("utf-8")

                # Return the base64 image and bounds in JSON response
                return JsonResponse(
                    {
                        "base64_image": f"data:image/png;base64,{img_base64}",
                        "bounds": [
                            [bounds[1], bounds[0]],  # [min_lat, min_lon]
                            [bounds[3], bounds[2]],  # [max_lat, max_lon]
                        ],
                    }
                )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def convert_shapefile(request):
    """Convert uploaded Shapefile to GeoJSON."""
    if request.method == "POST" and request.FILES.getlist("files"):
        try:
            uploaded_files = {
                file.name: file for file in request.FILES.getlist("files")
            }
            with tempfile.TemporaryDirectory() as temp_dir:
                for file_name, uploaded_file in uploaded_files.items():
                    with open(f"{temp_dir}/{file_name}", "wb") as temp_file:
                        temp_file.write(uploaded_file.read())

                gdf = gpd.read_file(temp_dir)
                geojson = gdf.to_json()

            return JsonResponse({"geojson": geojson})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def get_shapefile_bounds(request):
    """Return the bounds of an uploaded shapefile."""
    if request.method == "POST" and request.FILES.getlist("files"):
        try:
            uploaded_files = {
                file.name: file for file in request.FILES.getlist("files")
            }
            with tempfile.TemporaryDirectory() as temp_dir:
                for file_name, uploaded_file in uploaded_files.items():
                    with open(f"{temp_dir}/{file_name}", "wb") as temp_file:
                        temp_file.write(uploaded_file.read())

                gdf = gpd.read_file(temp_dir)
                bounds = gdf.total_bounds.tolist()

            return JsonResponse({"bounds": bounds})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


import io
import base64
import numpy as np
from PIL import Image
from rasterio import open as raster_open
from rasterio.warp import transform_bounds
from rasterio.plot import reshape_as_image
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

# ModuleNotFoundError: No module named 'PIL'

# class ConvertTiffAPIView(APIView):
#     parser_classes = [MultiPartParser, FormParser]  # To handle file uploads

#     def post(self, request, *args, **kwargs):
#         try:
#             # Get the uploaded file
#             uploaded_file = request.FILES['file']
#             file_content = uploaded_file.read()

#             # Open the TIFF file from the uploaded bytes
#             with raster_open(io.BytesIO(file_content)) as src:
#                 # Transform bounds to WGS84 if necessary
#                 if src.crs and src.crs.to_string() != "EPSG:4326":
#                     bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
#                 else:
#                     bounds = src.bounds

#                 # Read and process the image data
#                 data = src.read(out_shape=(src.count, src.height // 10, src.width // 10))
#                 data = reshape_as_image(data[:3])  # RGB bands

#                 # Normalize data
#                 epsilon = 1e-8
#                 data_normalized = ((data - data.min()) / (data.max() - data.min() + epsilon) * 255).astype(np.uint8)

#                 # Convert to RGBA (adding alpha channel)
#                 img = Image.fromarray(data_normalized)
#                 img = img.convert("RGBA")

#                 # Replace black pixels with transparent ones
#                 datas = img.getdata()
#                 new_data = [
#                     (0, 0, 0, 0) if item[0] < 10 and item[1] < 10 and item[2] < 10 else item
#                     for item in datas
#                 ]
#                 img.putdata(new_data)

#                 # Save the image to a byte array
#                 img_byte_arr = io.BytesIO()
#                 img.save(img_byte_arr, format='PNG')

#                 # Convert image to base64 string
#                 img_byte_arr.seek(0)  # Reset pointer to the beginning of the image byte array
#                 img_base64 = base64.b64encode(img_byte_arr.read()).decode('utf-8')

#                 # Return the base64 image and bounds in JSON response
#                 return Response({
#                     'base64_image': f"data:image/png;base64,{img_base64}",
#                     'bounds': [
#                         [bounds[1], bounds[0]],  # [min_lat, min_lon]
#                         [bounds[3], bounds[2]]   # [max_lat, max_lon]
#                     ]
#                 }, status=status.HTTP_200_OK)

#         except Exception as e:
#             return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

import requests
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


class ConvertTiffAPIView(APIView):
    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]  # Added JSONParser for JSON requests

    def post(self, request, *args, **kwargs):
        try:
            # Check if a URL is provided in the request
            file_url = request.data.get("file_url")

            if file_url:
                # Download the file from the provided URL
                response = requests.get(file_url, stream=True)
                if response.status_code != 200:
                    return Response(
                        {"error": "Failed to fetch the file from the provided URL"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                file_content = response.content
            else:
                # Get the uploaded file from the request
                uploaded_file = request.FILES["file"]
                file_content = uploaded_file.read()

            # Open the TIFF file from the downloaded or uploaded bytes
            with raster_open(io.BytesIO(file_content)) as src:
                # Transform bounds to WGS84 if necessary
                if src.crs and src.crs.to_string() != "EPSG:4326":
                    bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                else:
                    bounds = src.bounds

                # Read and process the image data
                data = src.read(
                    out_shape=(src.count, src.height // 10, src.width // 10)
                )
                data = reshape_as_image(data[:3])  # RGB bands

                # Normalize data
                epsilon = 1e-8
                data_normalized = (
                    (data - data.min()) / (data.max() - data.min() + epsilon) * 255
                ).astype(np.uint8)

                # Convert to RGBA (adding alpha channel)
                img = Image.fromarray(data_normalized)
                img = img.convert("RGBA")

                # Replace black pixels with transparent ones
                datas = img.getdata()
                new_data = [
                    (
                        (0, 0, 0, 0)
                        if item[0] < 10 and item[1] < 10 and item[2] < 10
                        else item
                    )
                    for item in datas
                ]
                img.putdata(new_data)

                # Save the image to a byte array
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format="PNG")

                # Convert image to base64 string
                img_byte_arr.seek(
                    0
                )  # Reset pointer to the beginning of the image byte array
                img_base64 = base64.b64encode(img_byte_arr.read()).decode("utf-8")

                # Return the base64 image and bounds in JSON response
                return Response(
                    {
                        "base64_image": f"data:image/png;base64,{img_base64}",
                        "bounds": [
                            [bounds[1], bounds[0]],  # [min_lat, min_lon]
                            [bounds[3], bounds[2]],  # [max_lat, max_lon]
                        ],
                    },
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
