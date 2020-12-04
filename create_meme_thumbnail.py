import boto3, ffmpeg, os
from secrets import token_urlsafe
from operator import itemgetter

s3 = boto3.client('s3')
BUCKET = 'meme-page-london'

def lambda_handler(event, context):
    original_file_ext = os.path.splitext(event['original_key'])[1]

    # Name of file in tmp directory
    tmp_original_file = f"/tmp/original{original_file_ext}"
    try:
        os.remove(tmp_original_file)
    except OSError:
        pass

    # Download file from S3
    s3.download_file(BUCKET, event["original_key"], tmp_original_file)

    # Get video info
    info = ffmpeg.probe(tmp_original_file)
    width, height = itemgetter("width", "height")(info["streams"][0])
    size = int(info["format"]["size"])
    duration = float(info["format"]["duration"])

    # Perform checks
    if original_file_ext.lower() == ".gif":
        if width < 250 or height < 250:
            return {"statusCode": 418, "errorMessage": "GIF must be at least 250x250 pixels"}
        if size > 5242880:
            return {"statusCode": 418, "errorMessage": "Maximum GIF size is 5MB"}
        if duration > 60:
            return {"statusCode": 418, "errorMessage": "GIF must be 60 seconds or less"}
    else:
        if width < 320 or height < 320:
            return {"statusCode": 418, "errorMessage": "Video must be at least 320x320 pixels"}
        if size > 15728640:
            return {"statusCode": 418, "errorMessage": "Maximum video size is 15MB"}
        if duration < 1:
            return {"statusCode": 418, "errorMessage": "Video must be at least 1 second"}
        if duration > 60:
            return {"statusCode": 418, "errorMessage": "Video must be 60 seconds or less"}

    # Open file in ffmpeg
    file = ffmpeg.input(tmp_original_file)

    # Name of thumbnail file in tmp directory
    tmp_thumbnail_name = "/tmp/thumbnail.webp"
    try:
        os.remove(tmp_thumbnail_name)
    except OSError:
        pass

    # Create 400x400 WEBP thumbnail and save to tmp_thumbnail_name
    file.output(
        tmp_thumbnail_name,
        r=1,
        vframes=1,
        vf=f"scale='if(gt(iw,ih), -2, min(400,iw))':'if(gt(ih,iw), -2, min(400,ih))',\
             crop='min(400,min(iw,ih))':'min(400,min(iw,ih))'"
    ).run()

    new_filename = f"{token_urlsafe(5)}.webp"
    thumbnail_path = os.path.join(event["path"], "thumbnail", new_filename)

    # Upload thumbnail back to S3
    s3.upload_file(
        tmp_thumbnail_name,
        BUCKET,
        thumbnail_path,
        ExtraArgs={"ContentType": "image/webp"}
    )

    return {
        "statusCode": 200,
        "body": {"thumbnail_path": thumbnail_path}
    }
