"""youtube-summarize 파이프라인 패키지."""
import sys


def setup_stdio() -> None:
    """stdout/stderr를 UTF-8로 강제한다.

    Windows 기본 콘솔(cp949 등)에서 한글/경로/기호 출력이 UnicodeEncodeError로
    죽는 것을 막는다. CLI 진입점에서 가장 먼저 호출한다.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
