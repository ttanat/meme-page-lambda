import boto3, ffmpeg, os

s3 = boto3.client('s3')
BUCKET = 'meme-page-london'

def lambda_handler(event, context):
    # Get file extension of original file
    original_file_ext = os.path.splitext(event['original_key'])[1]

    # Name of original file in tmp directory => old.{ext}
    tmp_original_file = f"/tmp/old{original_file_ext}"
    try:
        os.remove(tmp_original_file)
    except OSError:
        pass

    # Download file from S3 and save to old.{ext}
    s3.download_file(BUCKET, event["original_key"], tmp_original_file)

    # Open file in ffmpeg
    file = ffmpeg.input(tmp_original_file)

    # Name of new video file in tmp directory
    tmp_new_file = "/tmp/video.mp4"
    try:
        os.remove(tmp_new_file)
    except OSError:
        pass

    if original_file_ext.lower() == ".gif":
        # Convert GIF to mp4 and save to "video.mp4" in tmp directory
        file.output(
            tmp_new_file,
            movflags="faststart",
            video_bitrate=0,
            crf=28,
            format="mp4",
            vcodec="libx264",
            pix_fmt="yuv420p",
            vf="scale=trunc(iw/2)*2:trunc(ih/2)*2"
        ).run()
    else:
        # Resize video to 720x720 video and save to "video.mp4" in tmp directory
        file.output(
            tmp_new_file,
            movflags="faststart",
            vcodec="libx264",
            crf=30,
            format="mp4",
            pix_fmt="yuv420p",
            vf=f"scale='min(720,iw)':'min(720,ih)'\
                 :force_original_aspect_ratio=decrease:force_divisible_by=2"
        ).run()

    # Upload video back to S3
    s3.upload_file(
        tmp_new_file,
        BUCKET,
        event["save_large_to"],
        ExtraArgs={"ContentType": "video/mp4"}
    )

    return {
        "statusCode": 200
    }
