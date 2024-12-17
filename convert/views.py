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

        #  HD clarity
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
