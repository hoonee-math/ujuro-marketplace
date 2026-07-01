import imageio_ffmpeg


def ffmpeg_exe() -> str:
    """번들된 ffmpeg 실행파일 절대경로."""
    return imageio_ffmpeg.get_ffmpeg_exe()
