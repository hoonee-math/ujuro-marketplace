---
name: setup-environment
description: 스킬 실행 전/중 환경 문제(파이썬·의존성·ffmpeg 없음, 또는 폴백용 node 없음, doctor 실패)가 있을 때 읽는다. 탐지 → 설치 시도 → 안내 순서로 환경을 갖춘다.
---

# 환경 준비 / 문제 해결 (setup-environment)

`pipeline.doctor` 가 실패하거나 명령이 계속 실패하면 이 순서로 진행한다.

> **설치 위치:** 라이브러리는 **사용자의 Python 환경(site-packages)** 에 설치된다.
> 플러그인/스킬 폴더엔 `.py` 코드만 있고, 여기에 라이브러리가 깔리지 않는다.

## 0) 진단
```bash
py --version        # 또는 python --version   (3.10+ 필요)
node -v             # 선택 — Node 폴백을 쓸 때만
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.doctor
```

## 1) Python (필수)
없거나 3.10 미만이면 설치를 시도/안내한다:
- Windows(winget): `winget install Python.Python.3.14`
- 수동 다운로드: https://www.python.org/downloads/windows/ (설치 시 **"Add python.exe to PATH"** 체크)

설치 후 **새 터미널**에서 `py --version` 재확인.

## 2) 라이브러리 (필수) — ffmpeg 포함
```bash
pip install -r "${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt"
```
- 설치 항목: `yt-dlp`(다운로드) · `python-pptx`(PPT) · `imageio-ffmpeg`(**ffmpeg 바이너리 번들** → 별도 ffmpeg 설치 불필요) · `pytest`.
- 실패 시: `python -m pip install --upgrade pip` 후 재시도, 또는 개별 설치
  `pip install yt-dlp python-pptx imageio-ffmpeg`.

## 3) Node (선택 — 폴백 전용)
기본 Python 백엔드엔 **불필요**. codex/Node 폴백을 쓸 때만:
- 다운로드: https://nodejs.org/ko/download
- 설치 방법 포스팅: https://happy-metamong.tistory.com/26

설치 후 `node -v` 확인. (폴백 사용법은 `references/backends/node-fallback.md`)

## 4) 계속 실패하면
- `doctor` 출력의 **실패 항목을 사용자에게 그대로** 보여주고, 위 해당 단계를 다시 시도.
- 권한/PATH 문제로 의심되면 **새 터미널(또는 재로그인)** 후 재확인.
- 그래도 막히면 **어느 단계에서 어떤 메시지로** 막혔는지 정리해 사용자에게 전달.
