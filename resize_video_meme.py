import boto3, ffmpeg, os
from secrets import token_urlsafe
from operator import itemgetter

s3 = boto3.client('s3')
bucket = 'meme-page-test'

def lambda_handler(event, context):
    video_data = [
        ("large", f"{token_urlsafe(5)}.mp4", 960),
        ("medium", f"{token_urlsafe(5)}.mp4", 640),
    ]

    thumbnail_data = [
        ("thumbnail", f"{token_urlsafe(5)}.webp", 480),
        ("small_thumbnail", f"{token_urlsafe(5)}.webp", 320),
    ]

    # Name of file in tmp directory
    tmp = f"/tmp/{os.path.split(event['file_key'])[1]}"

    # Download file from S3
    s3.download_file(bucket, event["file_key"], tmp)

    # Get dimensions of video
    info = ffmpeg.probe(tmp)
    width, height = itemgetter("width", "height")(info["streams"][0])

    # Perform checks
    if width < 320 or height < 320:
        return {"statusCode": 418, "errorMessage": "Video must be at least 320x320 pixels"}
    if int(info["format"]["size"]) > 15728640:
        return {"statusCode": 418, "errorMessage": "Maximum video size is 15MB"}
    duration = float(info["format"]["duration"])
    if duration < 1:
        return {"statusCode": 418, "errorMessage": "Video must be at least 1 second"}
    if duration > 60:
        return {"statusCode": 418, "errorMessage": "Video must be 60 seconds or less"}

    # Check if have to resize video twice (remove from data if not)
    if width <= 640 and height <= 640:
        video_data.pop(0)
    # Check if have to create thumbnail twice (remove from data if not)
    if width == 320 and height == 320:
        thumbnail_data.pop(0)

    # Open file in ffmpeg
    file = ffmpeg.input(tmp)

    # Resize to 960x960 and 640x640 videos
    for folder, fname, size in video_data:
        # Name of new video file in tmp directory
        new_tmp = f"/tmp/{size}.mp4"
        try:
            os.remove(new_tmp)
        except OSError:
            pass

        # Process video
        file.output(
            new_tmp,
            movflags="faststart",
            vcodec="libx264",
            crf=33,
            format="mp4",
            pix_fmt="yuv420p",
            vf=f"scale='min({size},iw)':'min({size},ih)'\
                 :force_original_aspect_ratio=decrease:force_divisible_by=2"
        ).run()

        # Upload video back to S3
        s3.upload_file(new_tmp, bucket, os.path.join(event["path"], folder, fname))

    # Resize to 480x480 and 320x320 WEBP thumbnails
    for folder, fname, size in thumbnail_data:
        # Name of thumbnail file in tmp directory
        new_tmp = f"/tmp/{size}.webp"
        try:
            os.remove(new_tmp)
        except OSError:
            pass

        # Create thumbnails
        file.output(
            new_tmp,
            r=1,
            vframes=1,
            vf=f"scale='if(gt(iw,ih), -2, min({size},iw))':'if(gt(ih,iw), -2, min({size},ih))',\
                 crop='min({size},min(iw,ih))':'min({size},min(iw,ih))'"
        ).run()

        # Upload thumbnail back to S3
        s3.upload_file(new_tmp, bucket, os.path.join(event["path"], folder, fname))

    return {
        "statusCode": 200,
        "body": [{"size": size, "filename": filename} for size, filename, _ in video_data + thumbnail_data]
    }
