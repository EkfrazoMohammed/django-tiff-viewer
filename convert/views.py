# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# import rasterio
# import numpy as np
# import io
# import base64
# from PIL import Image
# from rasterio.warp import transform_bounds
# from concurrent.futures import ThreadPoolExecutor

# @csrf_exempt
# def convert_tiff(request):
#     """Convert a TIFF file to PNG with transparent background using concurrent processing."""
#     if request.method == "POST" and request.FILES.get("file"):
#         try:
#             # Get the uploaded file
#             uploaded_file = request.FILES.get("file")
#             if not uploaded_file:
#                 return JsonResponse({"error": "No file uploaded"}, status=400)

#             # Read the file into memory
#             contents = uploaded_file.read()

#             # Open the TIFF file from the uploaded bytes
#             with rasterio.Env(GDAL_NUM_THREADS="ALL_CPUS"):  # Enable concurrent processing
#                 with rasterio.open(io.BytesIO(contents)) as src:
#                     # Transform bounds to WGS84 if necessary
#                     bounds = (
#                         transform_bounds(src.crs, "EPSG:4326", *src.bounds)
#                         if src.crs != "EPSG:4326"
#                         else src.bounds
#                     )

#                     # Read and process the image data concurrently
#                     def read_band(band):
#                         return src.read(band)

#                     with ThreadPoolExecutor() as executor:
#                         # Use ThreadPoolExecutor to read bands concurrently
#                         bands = list(executor.map(read_band, [1, 2, 3]))
#                         data = np.stack(bands, axis=-1)  # Combine bands into H x W x C

#                     # Normalize the image data if needed
#                     if np.issubdtype(data.dtype, np.floating):
#                         data = np.nan_to_num(data)  # Replace NaN with 0
#                         data = ((data - data.min()) / (data.max() - data.min()) * 255).astype(np.uint8)

#                     # Create an RGBA image
#                     img = Image.fromarray(data)
#                     img = img.convert("RGBA")

#                     # Replace black pixels with transparency
#                     np_data = np.array(img)
#                     black_pixels = np.all(np_data[:, :, :3] < 10, axis=-1)  # Threshold for black pixels
#                     np_data[black_pixels, 3] = 0  # Set alpha to 0 for black pixels
#                     img = Image.fromarray(np_data)

#                     # Save the image to a byte array
#                     img_byte_arr = io.BytesIO()
#                     img.save(img_byte_arr, format="PNG", optimize=True)

#                     # Convert image to base64 string
#                     img_byte_arr.seek(0)
#                     img_base64 = base64.b64encode(img_byte_arr.read()).decode("utf-8")

#                     # Return the base64 image and bounds in JSON response
#                     return JsonResponse(
#                         {
#                             "base64_image": f"data:image/png;base64,{img_base64}",
#                             "bounds": [
#                                 [bounds[1], bounds[0]],  # [min_lat, min_lon]
#                                 [bounds[3], bounds[2]],  # [max_lat, max_lon]
#                             ],
#                         }
#                     )
#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=500)

#     return JsonResponse({"error": "Invalid request"}, status=400)

# import dask
# print(dask.__version__)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import rasterio
import numpy as np
import io
import base64
from PIL import Image
from rasterio.warp import transform_bounds
import dask.array as da
from dask import delayed

@csrf_exempt
def convert_tiff(request):
    """Convert a TIFF file to PNG with transparent background using Dask for processing."""
    if request.method == "POST" and request.FILES.get("file"):
        try:
            # Get the uploaded file
            uploaded_file = request.FILES.get("file")
            if not uploaded_file:
                return JsonResponse({"error": "No file uploaded"}, status=400)

            # Read the file into memory
            contents = uploaded_file.read()

            # Open the TIFF file from the uploaded bytes
            with rasterio.Env(GDAL_NUM_THREADS="ALL_CPUS"):  # Enable concurrent processing
                with rasterio.open(io.BytesIO(contents)) as src:
                    # Transform bounds to WGS84 if necessary
                    bounds = (
                        transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                        if src.crs != "EPSG:4326"
                        else src.bounds
                    )

                    # Read the bands into Dask arrays
                    def read_band(band):
                        return delayed(src.read)(band)

                    # Use Dask to read all bands concurrently
                    dask_bands = [read_band(band) for band in [1, 2, 3]]

                    # Compute the results of the Dask delayed tasks
                    computed_bands = [b.compute() for b in dask_bands]
                    data = np.stack(computed_bands, axis=-1)  # Combine bands into H x W x C

                    # Normalize the image data if needed
                    if np.issubdtype(data.dtype, np.floating):
                        data = np.nan_to_num(data)  # Replace NaN with 0
                        data = ((data - data.min()) / (data.max() - data.min()) * 255).astype(np.uint8)

                    # Create an RGBA image
                    img = Image.fromarray(data)
                    img = img.convert("RGBA")

                    # Replace black pixels with transparency
                    np_data = np.array(img)
                    black_pixels = np.all(np_data[:, :, :3] < 10, axis=-1)  # Threshold for black pixels
                    np_data[black_pixels, 3] = 0  # Set alpha to 0 for black pixels
                    img = Image.fromarray(np_data)

                    # Save the image to a byte array
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


