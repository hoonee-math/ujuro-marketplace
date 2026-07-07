"""YouTube → PPT CLI. Claude(Code)가 스킬 안내에 따라 Bash로 호출한다.

  python -m pipeline.run collect <url>      # 오디오·자막·대본 준비 → workdir 출력
  python -m pipeline.run render <video-id>  # analysis.json → 트림 MP3 + PPT (A4 가로 compact)
  python -m pipeline.run render-a4 <video-id> [--mode first|all] [--max-per-page 27]  # A4 프린트 덱
  python -m pipeline.run embed-audio <video-id> [--leadin <초>]  # 음성 포함 자동재생 덱 생성
  python -m pipeline.run retrim <video-id> --coords original|edited [--intro/--outro/--front/--back]
"""
import argparse
import json

from pipeline import setup_stdio, tools
from pipeline.build_a4 import MODES as A4_MODES, DEFAULT_MAX_PER_PAGE


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False))


def main():
    setup_stdio()
    ap = argparse.ArgumentParser(prog="pipeline.run")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="다운로드+대본")
    c.add_argument("url")

    r = sub.add_parser("render", help="analysis.json → 트림+PPT")
    r.add_argument("video_id")

    ra = sub.add_parser("render-a4", help="A4 세로 프린트 덱 (영어 예문 연습 인쇄물)")
    ra.add_argument("video_id")
    ra.add_argument("--mode", default="first", choices=sorted(A4_MODES),
                    help="프린트 포맷 (기본 first: 패턴별 대표 예문 1문장씩)")
    ra.add_argument("--max-per-page", type=int, default=DEFAULT_MAX_PER_PAGE,
                    help=f"페이지당 최대 줄 수 (기본 {DEFAULT_MAX_PER_PAGE})")

    ea = sub.add_parser("embed-audio", help="음성 포함 자동재생 덱 생성")
    ea.add_argument("video_id")
    ea.add_argument("--leadin", type=float, default=1.0,
                    help="각 구간을 시작점보다 이만큼 앞당겨 자름(초, 기본 1.0). 끝은 그대로.")

    rt = sub.add_parser("retrim", help="트림만 재조정")
    rt.add_argument("video_id")
    rt.add_argument("--coords", required=True, choices=["original", "edited"])
    rt.add_argument("--intro", type=float)
    rt.add_argument("--outro", type=float)
    rt.add_argument("--front", type=float)
    rt.add_argument("--back", type=float)

    args = ap.parse_args()
    if args.cmd == "collect":
        _print(tools.collect(args.url))
    elif args.cmd == "render":
        _print(tools.render(args.video_id))
    elif args.cmd == "render-a4":
        _print(tools.render_a4(args.video_id, mode=args.mode,
                               max_per_page=args.max_per_page))
    elif args.cmd == "embed-audio":
        _print(tools.embed_audio(args.video_id, leadin=args.leadin))
    elif args.cmd == "retrim":
        _print(tools.retrim(args.video_id, args.coords, intro=args.intro,
                            outro=args.outro, front=args.front, back=args.back))


if __name__ == "__main__":
    main()
