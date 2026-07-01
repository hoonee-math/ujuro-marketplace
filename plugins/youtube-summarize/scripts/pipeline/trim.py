import subprocess

from pipeline.ffmpeg_bin import ffmpeg_exe


def trim(original_mp3, intro_end: float, outro_start: float, out_path) -> None:
    if not (0 <= intro_end < outro_start):
        raise ValueError("need 0 <= intro_end < outro_start")
    cmd = [
        ffmpeg_exe(), "-y",
        "-i", str(original_mp3),
        "-ss", str(intro_end), "-to", str(outro_start),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
