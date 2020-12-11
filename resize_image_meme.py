import os

import boto3
from PIL import Image
from PIL.ImageOps import exif_transpose


s3 = boto3.client('s3')
BUCKET = "meme-page-london"


def lambda_handler(event, context):
    # Get image extension
    ext = os.path.splitext(event["get_file_at"])[1]

    tmp_original_path = f"/tmp/original{ext}"

    # Download original image to original.<ext>
    s3.download_file(BUCKET, event["get_file_at"], tmp_original_path)

    # Open original image
    with exif_transpose(Image.open(tmp_original_path).convert("RGB")) as img:
        # Get keyword arguments for saving images
        kwargs = {"optimize": True, "quality": 70}
        # Get ICC profile
        if img.info.get("icc_profile"):
            kwargs["icc_profile"] = img.info["icc_profile"]

        """ Resize and overwrite original image """
        # Resize to maximum 960x960
        img.thumbnail((960, 960))
        # Overwrite downloaded file (tmp)
        img.save(tmp_original_path, **kwargs)
        # Get content type of image
        content_type = "image/png" if ext.lower() == ".png" else "image/jpeg"
        # Upload resized back to original path in S3 (overwrite)
        s3.upload_file(
            tmp_original_path,
            BUCKET,
            event["get_file_at"],
            ExtraArgs={"ContentType": content_type}
        )

        """ Resize to create large WEBP image """
        tmp_large_path = "/tmp/large.webp"
        # Write large WEBP image to tmp directory
        img.save(tmp_large_path, **kwargs, format="WEBP")
        # Upload large WEBP image to S3
        s3.upload_file(
            tmp_large_path,
            BUCKET,
            event["large_key"],
            ExtraArgs={"ContentType": "image/webp"}
        )

        """ Create WEBP thumbnail """
        tmp_thumbnail_path = "/tmp/thumb.webp"
        # Get image width and height
        width, height = img.size
        # Get length of square to crop out of image
        crop_size = min(img.size)
        # Crop and save thumbnail to tmp directory
        with img.crop((
            (width - crop_size) // 2,
            (height - crop_size) // 2,
            (width + crop_size) // 2,
            (height + crop_size) // 2
        )) as tmp:
            tmp.thumbnail((400, 400))
            tmp.save(tmp_thumbnail_path, **kwargs, format="WEBP")
        # Upload WEBP thumbnail to S3
        s3.upload_file(
            tmp_thumbnail_path,
            BUCKET,
            event["thumbnail_key"],
            ExtraArgs={"ContentType": "image/webp"}
        )

    return {"statusCode": 200}
