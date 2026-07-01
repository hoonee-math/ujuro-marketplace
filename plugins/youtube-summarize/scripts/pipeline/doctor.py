import importlib
import subprocess
import sys

from pipeline import setup_stdio
from pipeline.paths import output_root
from pipeline.ffmpeg_bin import ffmpeg_exe

_PKGS = ["yt_dlp", "pptx"]


def check_environment() -> dict:
    checks = []
    checks.append({"name": "python",
                   "ok": sys.version_info >= (3, 10),
                   "detail": f"{sys.version_info.major}.{sys.version_info.minor}"})
    for mod in _PKGS:
        try:
            importlib.import_module(mod)
            checks.append({"name": f"pkg:{mod}", "ok": True, "detail": "import ok"})
        except Exception as e:
            checks.append({"name": f"pkg:{mod}", "ok": False, "detail": str(e)})
    try:
        out = subprocess.run([ffmpeg_exe(), "-version"], capture_output=True, text=True)
        checks.append({"name": "ffmpeg", "ok": out.returncode == 0,
                       "detail": (out.stdout.splitlines() or ["no output"])[0]})
    except Exception as e:
        checks.append({"name": "ffmpeg", "ok": False, "detail": str(e)})
    try:
        p = output_root() / ".write_test"
        p.write_text("ok", encoding="utf-8")
        p.unlink()
        checks.append({"name": "output_dir", "ok": True, "detail": str(output_root())})
    except Exception as e:
        checks.append({"name": "output_dir", "ok": False, "detail": str(e)})
    # node는 선택(폴백 전용) — 없어도 기본 Python 백엔드는 동작한다
    try:
        nv = subprocess.run(["node", "-v"], capture_output=True, text=True)
        node_ok = nv.returncode == 0
        checks.append({"name": "node (선택, 폴백용)", "ok": node_ok, "optional": True,
                       "detail": nv.stdout.strip() if node_ok else "미설치 — 기본 백엔드엔 불필요"})
    except Exception:
        checks.append({"name": "node (선택, 폴백용)", "ok": False, "optional": True,
                       "detail": "미설치 — 기본 백엔드엔 불필요"})
    return {"ok": all(c["ok"] for c in checks if not c.get("optional")), "checks": checks}


def format_report(rep: dict) -> str:
    head = "환경 진단: " + ("[OK] 모두 정상" if rep["ok"] else "[WARN] 문제 발견")

    def _mark(c):
        return "OK" if c["ok"] else ("--" if c.get("optional") else "FAIL")

    lines = [head] + [f"  [{_mark(c)}] {c['name']}: {c['detail']}" for c in rep["checks"]]
    if not rep["ok"]:
        lines.append("  -> 설치/복구 안내: references/steps/setup-environment.md")
    return "\n".join(lines)


if __name__ == "__main__":
    setup_stdio()
    print(format_report(check_environment()))
