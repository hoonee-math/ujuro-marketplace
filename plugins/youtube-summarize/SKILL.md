---
name: youtube-summarize
description: YouTube 링크나 사용자가 제공한 영어 회화 자료를 학습용 PPT(+편집 MP3)로 만든다. 트리거 예 - "이 링크로 영어 학습 ppt 만들어줘", "유튜브 영어회화 정리해줘", "영어 회화 ppt 만들어줘", "이 패턴들 ppt로 만들어줘", "make a study PPT from this YouTube video". 기계 작업(다운로드/트림/렌더)은 번들 스크립트, 대본→덱 분석은 Claude가 한다.
---

# YouTube → 학습 PPT (youtube-summarize)

YouTube 영상 또는 **사용자가 제공한 영어 회화 자료**를 편집된 MP3 + 학습 PPT로 만든다.
역할 분담: **기계 작업(다운로드/트림/렌더)은 스크립트, 대본→덱 분석은 너(Claude).**

## 준비 (최초 1회)
```bash
pip install -r "${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt"
```
환경 점검: `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.doctor`
- doctor가 실패하거나 Python/의존성/ffmpeg(또는 폴백용 Node) 문제가 보이면
  → `references/steps/setup-environment.md` 를 읽고 설치/복구를 진행·안내한다.

## 실행 규칙 (중요)
- 모든 파이프라인 명령은 **사용자의 현재 작업 폴더(cwd)에서** 실행한다.
  **`cd` 로 플러그인 폴더로 이동하지 말 것** — 산출물이 cwd에 저장되어야 하기 때문.
- 파이프라인은 `PYTHONPATH` 로 부른다:
  ```bash
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.run <cmd> ...
  ```
- 산출물: `<cwd>/youtube-summarize/<제목>-[id]/` 에 `slides.pptx` + `audio.trimmed.mp3`
  (옵션으로 음성 포함 자동재생 `slides.autoplay.pptx`). 중간물은 `.work/`, 재편집 백업은 `.history/`.

## 라우터 (입력 모드 → 분류 → 분기 → 렌더)

### 0) 입력 모드 감지
- 사용자가 **영어 회화 자료(패턴 텍스트)를 붙여넣음** → **자료 모드**:
  `references/steps/from-material.md` 를 읽고 그대로 따른다. (아래 1~4는 건너뜀)
- **URL만** 있음 → **영상 모드**: 아래 1)로.

### 1) 수집 (영상 모드)
```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.run collect "<URL>"
```
→ `{"video_id","workdir","work_dir","analysis_path",...}` JSON. (자막 429 등 실패 시 잠시 후 재시도.)

### 2) 1차 분석 (triage) — 영상 유형 판정
반환된 `work_dir` 의 `transcript.json`(자막 큐)과 `info.json`(제목·설명·챕터)을 Read로 읽고 유형 판정:
- **english_conversation** — 다양한 영어 표현/패턴을 예문과 반복으로 학습하는 영상 → **지원**
- 그 외(`general_talk`/`lecture`/`news`/`interview`/`music`/`tutorial`/`other`) → **미지원**

### 3) 분기
- **english_conversation** → `references/types/english-conversation.md` 를 읽고, 그 지침대로
  `analysis.json` 을 `analysis_path`(= `.work/analysis.json`)에 Write.
- **미지원** → 아래 문구를 출력하고 **여기서 멈춘다** (수집물은 그대로 둠):
  > 이 영상은 **'{추정 유형}'** 으로 보입니다. 현재 youtube-summarize는 **'영어 회화연습'**
  > 유형만 정식 지원합니다. 이 유형은 **아직 지원하지 않습니다.** (지원 유형은 계속 추가될 예정이에요.)

### 4) 렌더
```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.run render <video-id>
```
→ `{"pptx_path","mp3_path","study_json_path","n_sentences"}`. 사용자에게 경로 안내.
- 덱은 A4 가로 compact 레이아웃(예문 영어+한글 한 줄, 긴 문장만 줄바꿈)으로 렌더된다.

### 5) (옵션) PPT에 음성 포함 — 렌더 후 사용자에게 물어본다
렌더 결과를 안내한 뒤 **"PPT에 음성을 넣어 슬라이드가 자동으로 재생·전환되는 버전도 만들까요?"** 라고 묻는다.
- **예** → 아래 실행. 각 슬라이드에 그 구간 오디오가 임베드되어 **열리면 자동재생 + 구간 길이만큼 뒤 자동 전환**되고, 아무 페이지로 점프해도 그 페이지 구간이 처음부터 재생된다.
  ```bash
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.run embed-audio <video-id>
  ```
  → `{"autoplay_pptx_path","n_content_slides","leadin_seconds","audio_seconds","locked_fallback"}`.
  - `--leadin <초>`(기본 1.0): 각 구간을 시작점보다 그만큼 앞당겨 자른다(앞 페이지와 살짝 겹침, 첫 단어 잘림 방지). 끝 시점은 그대로.
  - `locked_fallback: true` 면 대상 파일이 PowerPoint에서 열려 있어 `slides.autoplay.new.pptx` 로 저장된 것 → 사용자에게 원본을 닫고 재실행하면 정식 이름으로 저장된다고 안내.
  - 안내: 자동재생/임베드 오디오는 **데스크톱 PowerPoint 기준**이다(Google Slides·Keynote에선 그대로 안 될 수 있음). 슬라이드 우상단에 작은 스피커 아이콘이 보이면 정상.
- **아니오** → 여기서 끝. (기본 `slides.pptx` 는 음성 없는 학습용 덱.)

### 6) (옵션) A4 프린트 버전 — 요청 시
사용자가 "프린트해서 연습", "A4로 뽑아줘", "인쇄용 정리" 등 **종이 인쇄물**을 원하면
→ `references/steps/a4-print.md` 를 읽고 진행한다. (포맷 여러 종 — 사용자에게 확인 후 `render-a4`)

## 재편집 (요청 시)
사용자가 "앞 5초 더 잘라", "인트로 1:10까지" 등 컷 조정을 요청하면
→ `references/steps/retrim-audio.md` 참조. (원본에서 재트림, 덮어쓰기 전 `.history` 백업)

## 환경 폴백
Python이 없거나 의존성 설치가 어려운 환경 → `references/backends/node-fallback.md` (codex/Node 파이프라인).

## 참고
- `cut` 좌표(트림) 판단은 유형 무관 공통: `{"intro_end":<본격 내용 시작초>, "outro_start":<마무리/홍보 시작초>}`.
  모든 `t_seconds` 는 **원본 오디오 기준**.
- 환경 문제 의심 시: `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.doctor`.
