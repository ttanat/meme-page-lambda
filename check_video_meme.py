import os
from operator import itemgetter

import boto3
import ffmpeg


s3 = boto3.client('s3')
BUCKET = 'meme-page-london'


def lambda_handler(event, context):
    # Get video extension
    ext = os.path.splitext(event["get_file_at"])[1]

    tmp_original_path = f"/tmp/original{ext}"

    # Download file from S3
    s3.download_file(BUCKET, event["get_file_at"], tmp_original_path)

    # Get video info
    info = ffmpeg.probe(tmp_original_path)
    width, height = itemgetter("width", "height")(info["streams"][0])
    size = int(info["format"]["size"])
    duration = float(info["format"]["duration"])

    # Perform checks
    if width < 320 or height < 320:
        return {"statusCode": 418, "errorMessage": "Video must be at least 320x320 pixels"}
    if size > 15728640:
        return {"statusCode": 418, "errorMessage": "Maximum video size is 15MB"}
    if duration < 1:
        return {"statusCode": 418, "errorMessage": "Video must be at least 1 second"}
    if duration > 60:
        return {"statusCode": 418, "errorMessage": "Video must be 60 seconds or less"}

    return {"statusCode": 200}
