import boto3, os
from PIL import Image
from secrets import token_urlsafe

s3 = boto3.client('s3')
tmp = "/tmp/image.jpg"
new = "/tmp/image.webp"


def lambda_handler(event, context):
    # Download original image to image.jpg
    s3.download_file('meme-page-test', event["original_key"], tmp)

    data = (
        ("large", f"{token_urlsafe(8)}.webp", (960, 960)),
        ("thumbnail", f"{token_urlsafe(8)}.webp", (400, 400)),
    )

    # Open image.jpg
    with Image.open(tmp) as img:
        """ Only create thumbnail if image is already <= 400x400 """
        if img.width <= 400 and img.height <= 400:
            data = data[1]

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
