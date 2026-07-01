"""YouTube → PPT CLI. Claude(Code)가 스킬 안내에 따라 Bash로 호출한다.

  python -m pipeline.run collect <url>      # 오디오·자막·대본 준비 → workdir 출력
  python -m pipeline.run render <video-id>  # workdir/analysis.json 읽어 트림 MP3 + PPT
  python -m pipeline.run embed-audio <video-id> [--leadin <초>]  # 음성 포함 자동재생 덱 생성
  python -m pipeline.run retrim <video-id> --coords original|edited [--intro/--outro/--front/--back]
"""
import argparse
import json

from pipeline import setup_stdio, tools


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
    elif args.cmd == "embed-audio":
        _print(tools.embed_audio(args.video_id, leadin=args.leadin))
    elif args.cmd == "retrim":
        _print(tools.retrim(args.video_id, args.coords, intro=args.intro,
                            outro=args.outro, front=args.front, back=args.back))


if __name__ == "__main__":
    main()
