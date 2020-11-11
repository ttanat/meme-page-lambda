import boto3, os
from PIL import Image
from secrets import token_urlsafe

s3 = boto3.client('s3')
tmp = "/tmp/image.jpg"
new = "/tmp/image.webp"


def lambda_handler(event, context):
    # Download original image to image.jpg
    s3.download_file('meme-page-test', event["file_key"], tmp)

    data = (
        ("large", f"{token_urlsafe(8)}.webp", (960, 960)),
        ("medium", f"{token_urlsafe(8)}.webp", (640, 640)),
        ("thumbnail", f"{token_urlsafe(8)}.webp", (480, 480)),
        ("small_thumbnail", f"{token_urlsafe(8)}.webp", (320, 320))
    )

    # Open image.jpg
    with Image.open(tmp) as img:
        """ Remove sizes that image is already smaller than """
        # Check that image dimensions is less than or equal to given number
        cd = lambda d: img.width <= d and img.height <= d
        # Find index at which to slice data
        i = 3 if cd(320) else 2 if cd(480) else 1 if cd(640) else 0
        data = data[i:]

        """ Resize image to different sizes and upload back to S3 """
        for size, fname, dimensions in data:
            # Resize image.jpg
            img.thumbnail(dimensions)
            # Save resized image to image.webp
            img.save(new, optimize=True, quality=70, format="WEBP")

            # Upload resized image.webp to key
            s3.upload_file(new, 'meme-page-test', os.path.join(event["path"], size, fname))

    return {
        "statusCode": 200,
        "body": [{"size": d[0], "filename": d[1]} for d in data]
    }
