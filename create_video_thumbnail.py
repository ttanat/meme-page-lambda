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
    # Remove file in tmp directory if exists (to avoid ffmpeg asking user input to overwrite file)
    try:
        os.remove(tmp_original_path)
    except OSError:
        pass

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

    # Open file in ffmpeg
    file = ffmpeg.input(tmp_original_path)

    tmp_thumbnail_path = "/tmp/thumb.webp"
    # Remove file in tmp directory if exists (to avoid ffmpeg asking user input to overwrite file)
    try:
        os.remove(tmp_thumbnail_path)
    except OSError:
        pass

    # Create 400x400 WEBP thumbnail and save to tmp_thumbnail_path
    file.output(
        tmp_thumbnail_path,
        r=1,
        vframes=1,
        q=70,
        vf="scale='if(gt(iw,ih), -2, min(400,iw))':'if(gt(ih,iw), -2, min(400,ih))', \
            crop='min(400,min(iw,ih))':'min(400,min(iw,ih))'"
    ).run()

    # If thumbnail file size is more than 50KB, then resize to lower (50) quality (default is 75)
    if os.path.getsize(tmp_thumbnail_path) > 51200:
        # Remove newly created thumbnail file
        os.remove(tmp_thumbnail_path)
        # Create lower quality thumbnail
        file.output(
            tmp_thumbnail_path,
            r=1,
            vframes=1,
            q=50,
            vf="scale='if(gt(iw,ih), -2, min(400,iw))':'if(gt(ih,iw), -2, min(400,ih))', \
                crop='min(400,min(iw,ih))':'min(400,min(iw,ih))'"
        ).run()

    # Upload thumbnail back to S3
    s3.upload_file(
        tmp_thumbnail_path,
        BUCKET,
        event["thumbnail_key"],
        ExtraArgs={"ContentType": "image/webp"}
    )

    return {"statusCode": 200}
