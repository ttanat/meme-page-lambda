import os
from contextlib import suppress

import boto3
import ffmpeg


s3 = boto3.client('s3')
BUCKET = 'meme-page-london'


def lambda_handler(event, context):
    # Get video extension
    ext = os.path.splitext(event["get_file_at"])[1]
    is_mov = ext == ".mov"

    tmp_original_path = f"/tmp/original{ext}"
    with suppress(OSError): os.remove(tmp_original_path)

    # Download file from S3
    s3.download_file(BUCKET, event["get_file_at"], tmp_original_path)

    # Open file in ffmpeg
    stream = ffmpeg.input(tmp_original_path)

    """ Create thumbnail file """
    tmp_thumbnail_path = "/tmp/thumb.webp"
    with suppress(OSError): os.remove(tmp_thumbnail_path)

    # Create 400x400 WEBP thumbnail and save to tmp_thumbnail_path
    stream.output(
        tmp_thumbnail_path,
        r=1,
        vframes=1,
        q=70,
        vf="scale='if(gt(iw,ih), -2, min(400,iw))':'if(gt(ih,iw), -2, min(400,ih))', \
            crop='min(400,min(iw,ih))':'min(400,min(iw,ih))'"
    ).overwrite_output().run()

    # If thumbnail file size is more than 50KB, then resize to lower (50) quality (default is 75)
    if os.path.getsize(tmp_thumbnail_path) > 51200:
        # Remove newly created thumbnail file
        with suppress(OSError): os.remove(tmp_thumbnail_path)
        # Create lower quality thumbnail
        stream.output(
            tmp_thumbnail_path,
            r=1,
            vframes=1,
            q=50,
            vf="scale='if(gt(iw,ih), -2, min(400,iw))':'if(gt(ih,iw), -2, min(400,ih))', \
                crop='min(400,min(iw,ih))':'min(400,min(iw,ih))'"
        ).overwrite_output().run()

    # Upload thumbnail back to S3
    s3.upload_file(
        tmp_thumbnail_path,
        BUCKET,
        event["thumbnail_key"],
        ExtraArgs={"ContentType": "image/webp"}
    )

    """ Create large file """

    original_size = os.path.getsize(tmp_original_path)

    # If original file is mp4 and size <= 100KB, then don't need to resize video
    if not is_mov and original_size <= 102400:
        return {"statusCode": 200}

    # Determine crf value depending on original file size (larger size -> increase crf -> size further reduced)
    if original_size < 1048576:
        # If size less than 1 MB
        crf = 28
    elif original_size < 5242880:
        # If size less than 5 MB
        crf = 29
    elif original_size < 9437184:
        # If size less than 9 MB
        crf = 30
    elif original_size < 13631488:
        # If size less than 13 MB
        crf = 32
    else:
        crf = 33

    tmp_large_path = "/tmp/large.mp4"
    with suppress(OSError): os.remove(tmp_large_path)

    # Resize video to maximum of 720x720 and save to "large.mp4" in tmp directory
    stream.output(
        tmp_large_path,
        movflags="faststart",
        vcodec="libx264",
        crf=crf,
        format="mp4",
        pix_fmt="yuv420p",
        vf="scale='min(720,iw)':'min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2"
    ).overwrite_output().run()

    if is_mov:
        upload_to = f'{os.path.splitext(event["get_file_at"])[0]}.mp4'
    else:
        upload_to = event["get_file_at"]

    # Upload resized video back to S3
    s3.upload_file(
        tmp_large_path,
        BUCKET,
        upload_to,
        ExtraArgs={"ContentType": "video/mp4"}
    )

    # Delete mov file
    if is_mov:
        s3.delete_object(Bucket=BUCKET, Key=event["get_file_at"])

    return {"statusCode": 200}
