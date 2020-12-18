import os

import boto3
import ffmpeg
from PIL import Image


s3 = boto3.client('s3')
BUCKET = "meme-page-london"


def lambda_handler(event, context):
    # Get image extension
    ext = os.path.splitext(event["get_file_at"])[1]

    tmp_original_path = f"/tmp/original{ext}"

    # Download original image to original.<ext>
    s3.download_file(BUCKET, event["get_file_at"], tmp_original_path)

    """ Create WEBP thumbnail """
    # Open GIF
    with Image.open(tmp_original_path).convert("RGB") as gif:
        tmp_thumbnail_path = "/tmp/thumb.webp"
        # Get image width and height
        width, height = gif.size
        # Get length of square to crop out of image
        crop_size = min(gif.size)
        # Crop and save thumbnail to tmp directory
        with gif.crop((
            (width - crop_size) // 2,
            (height - crop_size) // 2,
            (width + crop_size) // 2,
            (height + crop_size) // 2
        )) as tmp:
            tmp.thumbnail((400, 400))
            tmp.save(tmp_thumbnail_path, optimize=True, quality=70, format="WEBP")
        # Upload WEBP thumbnail to S3
        s3.upload_file(
            tmp_thumbnail_path,
            BUCKET,
            event["thumbnail_key"],
            ExtraArgs={"ContentType": "image/webp"}
        )

    """ Create large mp4 file """
    tmp_large_path = "/tmp/large.mp4"
    # Remove file in tmp directory if exists (to avoid ffmpeg asking user input to overwrite file)
    try:
        os.remove(tmp_large_path)
    except OSError:
        pass
    # Open original GIF file
    stream = ffmpeg.input(tmp_original_path)
    # Convert GIF to mp4 and save to "large.mp4" in tmp directory
    stream.output(
        tmp_large_path,
        movflags="faststart",
        video_bitrate=0,
        crf=28,
        format="mp4",
        vcodec="libx264",
        pix_fmt="yuv420p",
        vf="scale='min(720,iw)':'min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2"
    ).overwrite_output().run()
    # Upload video back to S3
    s3.upload_file(
        tmp_large_path,
        BUCKET,
        event["large_key"],
        ExtraArgs={"ContentType": "video/mp4"}
    )

    return {"statusCode": 200}
