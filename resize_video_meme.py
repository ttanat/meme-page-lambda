import boto3, ffmpeg, os
from secrets import token_urlsafe
from operator import itemgetter

s3 = boto3.client('s3')
BUCKET = 'meme-page-london'

def lambda_handler(event, context):
    video_data = {
        "folder": "large",
        "filename": f"{token_urlsafe(5)}.mp4",
        "dimension": 720
    }

    thumbnail_data = {
        "folder": "thumbnail",
        "filename": f"{token_urlsafe(5)}.webp",
        "dimension": 400
    }

    # Name of file in tmp directory
    tmp = f"/tmp/{os.path.split(event['original_key'])[1]}"

    # Download file from S3
    s3.download_file(BUCKET, event["original_key"], tmp)

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

    # Open file in ffmpeg
    file = ffmpeg.input(tmp)

    # Resize to 720x720 video
    # Name of new video file in tmp directory
    new_tmp = f"/tmp/video.mp4"
    try:
        os.remove(new_tmp)
    except OSError:
        pass

    # For readability
    vd = video_data["dimension"]

    # Process video
    file.output(
        new_tmp,
        movflags="faststart",
        vcodec="libx264",
        crf=33,
        format="mp4",
        pix_fmt="yuv420p",
        vf=f"scale='min({vd},iw)':'min({vd},ih)'\
             :force_original_aspect_ratio=decrease:force_divisible_by=2"
    ).run()

    # Upload video back to S3
    s3.upload_file(new_tmp, BUCKET, os.path.join(event["path"], video_data["folder"], video_data["filename"]))

    # Resize to 400x400 WEBP thumbnail
    # Name of thumbnail file in tmp directory
    new_tmp = f"/tmp/thumbnail.webp"
    try:
        os.remove(new_tmp)
    except OSError:
        pass

    # For readability
    td = thumbnail_data["dimension"]

    # Create thumbnails
    file.output(
        new_tmp,
        r=1,
        vframes=1,
        vf=f"scale='if(gt(iw,ih), -2, min({td},iw))':'if(gt(ih,iw), -2, min({td},ih))',\
             crop='min({td},min(iw,ih))':'min({td},min(iw,ih))'"
    ).run()

    # Upload thumbnail back to S3
    s3.upload_file(
        new_tmp,
        BUCKET,
        os.path.join(event["path"], thumbnail_data["folder"], thumbnail_data["filename"]),
        ExtraArgs={"ContentType": "image/webp"}
    )

    return {
        "statusCode": 200,
        "body": [
            {"size": video_data["folder"], "filename": video_data["filename"]},
            {"size": thumbnail_data["folder"], "filename": thumbnail_data["filename"]}
        ]
    }
