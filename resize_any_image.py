import boto3, os
from PIL import Image
from secrets import token_urlsafe

s3 = boto3.client('s3')

BUCKET_NAME = "meme-page-london"


def lambda_handler(event, context):
    # Get image extension
    ext = os.path.splitext(event["file_key"])[1]

    tmp = f"/tmp/image{ext}"

    # Download original image to tmp
    s3.download_file(BUCKET_NAME, event["file_key"], tmp)

    # Open image.jpg
    with Image.open(tmp) as img:
        """ Resize image to specified size and upload back to S3 """
        # Resize image
        img.thumbnail(event["dimensions"])
        # Save resized image
        img.save(tmp, optimize=True, quality=70)

    # Get content type of file
    content_type = "image/png" if ext.lower() == ".png" else "image/jpeg"

    # Upload resized back to same path (overwrite)
    s3.upload_file(tmp, BUCKET_NAME, event["file_key"], ExtraArgs={"ContentType": content_type})

    return {
        "statusCode": 200
    }
