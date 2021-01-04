import os

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
    info = ffmpeg.probe(tmp_original_path, v="error", show_entries="format=size,duration")

    # Check size (allow missing size info since size already checked on upload)
    size = int(info["format"].get("size", 0))
    if size > 15728640:
        return {"statusCode": 418, "errorMessage": "Maximum video size is 15MB"}

    # Check duration
    duration = float(info["format"].get("duration", 0))
    if duration == 0:
        return {"statusCode": 418, "errorMessage": "Video file missing information"}
    if duration < 1:
        return {"statusCode": 418, "errorMessage": "Video must be at least 1 second"}
    if duration > 60:
        return {"statusCode": 418, "errorMessage": "Video must be 60 seconds or less"}

    # Get video info
    info = ffmpeg.probe(tmp_original_path, v="error", select_streams="v:0", show_entries="stream=width,height,display_aspect_ratio,avg_frame_rate")

    streams = info["streams"][0]

    # Check width and height
    width = streams.get("width")
    height = streams.get("height")
    if not width or not height:
        return {"statusCode": 418, "errorMessage": "Video file missing information"}
    if width < 320 or height < 320:
        return {"statusCode": 418, "errorMessage": "Video must be at least 320x320 pixels"}

    # Check aspect ratio using width and height
    # Allow some extra room past 16:9 aspect ratio, e.g. for 720x404
    if not 1 / 1.8 < width / height < 1.8:
        return {"statusCode": 418, "errorMessage": "Aspect ratio must be between 16:9 and 9:16"}
    # Check aspect ratio using aspect ratio info if present
    aspect_ratio = streams.get("display_aspect_ratio")
    if aspect_ratio:
        width_ar, height_ar = [float(x) for x in aspect_ratio.split(":")]
        if not 1 / 1.8 < width_ar / height_ar < 1.8:
            return {"statusCode": 418, "errorMessage": "Aspect ratio must be between 16:9 and 9:16"}

    # Check frame rate (allow missing frame rate info)
    frame_rate = streams.get("avg_frame_rate", "0")
    if eval(frame_rate) > 60:
        return {"statusCode": 418, "errorMessage": "Maximum 60 frames per second"}

    return {"statusCode": 200}
