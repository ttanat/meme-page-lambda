import boto3, os
from PIL import Image

s3 = boto3.client('s3')

BUCKET = "meme-page-london"


def lambda_handler(event, context):
    # Get image extension
    ext = os.path.splitext(event["image_key"])[1]

    tmp = f"/tmp/image{ext}"

    # Download original image to image.jpg
    s3.download_file(BUCKET, event["image_key"], tmp)

    # Open image.jpg
    with Image.open(tmp) as img:
        """ Resize image to specified size and upload back to S3 """

        # Resize to 400x400
        img.thumbnail((400, 400))
        img.save(tmp, optimize=True, quality=70)

        content_type = "image/png" if ext.lower() == ".png" else "image/jpeg"
        extra_args = {"ContentType": content_type}

        # Upload resized image back to same path (overwrite)
        s3.upload_file(tmp, BUCKET, event["image_key"], ExtraArgs=extra_args)

        # Resize to 48x48
        img.thumbnail((48, 48))
        img.save(tmp, optimize=True, quality=70)

        # Upload back to small image path
        s3.upload_file(tmp, BUCKET, event["small_image_key"], ExtraArgs=extra_args)

    return {
        "statusCode": 200
    }
