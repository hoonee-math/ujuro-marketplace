---
name: node-fallback
description: 기본 Python 백엔드를 못 쓰는 환경(파이썬/의존성 설치 불가 등)에서 참고하는 대체 경로. 분석을 외부 codex(Node) 파이프라인이 자동 수행한다.
---

# Node 백엔드 폴백 (codex)

기본 백엔드는 **Python-claude**다(분석을 Claude가 직접 → 품질 최고). 이 문서는 **Python을 못 쓰는 환경**을 위한 대체 안내다.

## 먼저 시도할 것
1. `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.doctor` 로 원인 파악.
2. 의존성만 문제면: `pip install -r "${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt"`.
3. Python 자체가 없으면 설치 안내(또는 아래 Node 경로).

## Node(codex) 파이프라인
- 성격: **분석까지 외부 `codex exec`(GPT)가 자동 수행**하는 완전 자동 파이프라인. Claude가 분석에 개입하지 않는다.
- 필요: Node.js + `codex` CLI + `pptxgenjs`, yt-dlp/ffmpeg(uvx).
- 참고 구현: `D:/Project-D/test-D/youtube/codex` (`bin/youtube-study.cmd <URL>` 가 다운로드→분석→렌더 5단계를 자동 실행).

## 현재 상태 (한계)
- 이 버전 플러그인에는 Node 백엔드가 **번들되어 있지 않다.** 위 참고 구현을 로컬에서 쓰거나, 정식 번들은 추후 과제.
- 결과 품질은 Python-claude가 우선이므로, 가능하면 Python 환경을 갖추는 것을 권장한다.
