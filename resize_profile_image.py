import os

import boto3
from PIL import Image
from PIL.ImageOps import exif_transpose

s3 = boto3.client('s3')

BUCKET = "meme-page-london"


def lambda_handler(event, context):
    # Get image extension
    ext = os.path.splitext(event["image_key"])[1]

    tmp = f"/tmp/image{ext}"

    # Download original image to image.jpg
    s3.download_file(BUCKET, event["image_key"], tmp)

    # Open image.jpg
    with exif_transpose(Image.open(tmp).convert("RGB")) as img:
        """ Resize image to specified size and upload back to S3 """

        # Get keyword arguments for saving images
        kwargs = {"optimize": True, "quality": 70}
        # Get ICC profile
        if img.info.get("icc_profile"):
            kwargs["icc_profile"] = img.info["icc_profile"]

        # Get image width and height
        width, height = img.size
        # Get length of square to crop out of image
        crop_size = min(img.size)
        # Crop center square out of image
        with img.crop((
            (width - crop_size) // 2,
            (height - crop_size) // 2,
            (width + crop_size) // 2,
            (height + crop_size) // 2
        )) as cropped_img:
            # Resize to 400x400
            cropped_img.thumbnail((400, 400))
            cropped_img.save(tmp, **kwargs)

            content_type = "image/png" if ext.lower() == ".png" else "image/jpeg"
            extra_args = {"ContentType": content_type}

            # Upload resized image back to same path (overwrite)
            s3.upload_file(tmp, BUCKET, event["image_key"], ExtraArgs=extra_args)

            # Resize to 96x96
            cropped_img.thumbnail((96, 96))
            cropped_img.save(tmp, **kwargs)

            # Upload back to small image path
            s3.upload_file(tmp, BUCKET, event["small_image_key"], ExtraArgs=extra_args)

    return {
        "statusCode": 200
    }
