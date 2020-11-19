import boto3, ffmpeg, os
from secrets import token_urlsafe
from operator import itemgetter

s3 = boto3.client('s3')
BUCKET = 'meme-page-london'

def lambda_handler(event, context):
    video_data = {
        "folder": "large",
        "filename": f"{token_urlsafe(5)}.mp4"
    }

    thumbnail_data = {
        "folder": "thumbnail",
        "filename": f"{token_urlsafe(5)}.webp"
    }

    # Name of file in tmp directory
    tmp = f"/tmp/{os.path.split(event['original_key'])[1]}"

    # Download file from S3
    s3.download_file(BUCKET, event["original_key"], tmp)

    # Get dimensions of gif
    info = ffmpeg.probe(tmp)
    width, height = itemgetter("width", "height")(info["streams"][0])

    # Perform checks
    if width < 280 or height < 280:
        return {"statusCode": 418, "errorMessage": "GIF must be at least 280x280 pixels"}
    if int(info["format"]["size"]) > 5242880:
        return {"statusCode": 418, "errorMessage": "Maximum GIF size is 5MB"}

    # Open file in ffmpeg
    file = ffmpeg.input(tmp)

    # Name of new video file in tmp directory
    new_tmp = f"/tmp/video.mp4"
    try:
        os.remove(new_tmp)
    except OSError:
        pass

    # Process gif to video
    file.output(
        new_tmp,
        movflags="faststart",
        video_bitrate=0,
        crf=28,
        format="mp4",
        vcodec="libx264",
        pix_fmt="yuv420p",
        vf="scale=trunc(iw/2)*2:trunc(ih/2)*2"
    ).run()

    # Upload video back to S3
    s3.upload_file(
        new_tmp,
        BUCKET,
        os.path.join(event["path"], video_data["folder"], video_data["filename"]),
        ExtraArgs={"ContentType": "video/mp4"}
    )

    # Create 400x400 WEBP thumbnail
    # Name of thumbnail file in tmp directory
    new_tmp = f"/tmp/thumbnail.webp"
    try:
        os.remove(new_tmp)
    except OSError:
        pass

    # Create thumbnail
    file.output(
        new_tmp,
        r=1,
        vframes=1,
        vf=f"scale='if(gt(iw,ih), -2, min(400,iw))':'if(gt(ih,iw), -2, min(400,ih))',\
             crop='min(400,min(iw,ih))':'min(400,min(iw,ih))'"
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
