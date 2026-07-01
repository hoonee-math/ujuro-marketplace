# youtube-summarize 파이프라인 (scripts)

기계 작업(다운로드·트림·렌더)을 담당하는 Python 파이프라인. 대본→덱 분석은 Claude가 SKILL.md에 따라 수행한다.

## 호출 방법

플러그인 안에 번들되어 있으므로 `PYTHONPATH` 로 부른다. **사용자의 작업 폴더(cwd)에서** 실행한다
(산출물이 cwd에 저장됨 — `cd` 로 이 폴더로 오지 말 것).

```bash
pip install -r "${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt"   # 최초 1회
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.doctor
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.run <cmd> ...
```

## 명령

| 명령 | 설명 | 출력(JSON) |
|------|------|------------|
| `collect "<URL>"` | 오디오+자막+메타 다운로드, 대본 생성 | `video_id, workdir, work_dir, analysis_path, title, ...` |
| `render <video-id>` | `.work/analysis.json` → 트림 MP3 + PPT | `pptx_path, mp3_path, study_json_path, n_sentences` |
| `embed-audio <video-id> [--leadin <초>]` | 슬라이드별 오디오 임베드(자동재생)+자동전환 덱 생성 | `autoplay_pptx_path, n_content_slides, leadin_seconds, audio_seconds, locked_fallback` |
| `retrim <video-id> --coords original\|edited [--intro/--outro/--front/--back <초>]` | 원본에서 재트림, 백업 후 덮어쓰기 | `pptx_path, mp3_path, backup_dir, backed_up, cut` |
| `doctor` | 환경 진단 | 텍스트 |

## 산출물 구조 (cwd 기준)

```
<cwd>/youtube-summarize/<제목>-[video-id]/
├── slides.pptx            # 최종물
├── audio.trimmed.mp3      # 최종물
├── slides.autoplay.pptx   # 최종물(옵션: embed-audio, 음성 포함 자동재생)
├── .work/                 # 중간물
│   ├── audio.source.mp3   #   원본(retrim 소스, 보존)
│   ├── audio.ko.vtt, info.json, transcript.json
│   ├── analysis.json      #   Claude가 작성
│   ├── cut.json, study.json
│   └── seg/               #   embed-audio 구간 오디오(seg01.mp3 …)
└── .history/<stamp>/      # retrim 덮어쓰기 전 백업
    ├── slides.pptx
    └── audio.trimmed.mp3
```

- 출력 루트는 기본 `cwd/youtube-summarize`. `YOUTUBE_SUMMARIZE_OUTPUT_DIR` 로 덮어쓸 수 있다(테스트용).
- stdout은 UTF-8 강제(`pipeline.setup_stdio`) — Windows cp949 콘솔에서도 안전. 스크립트 출력에 이모지 미사용.

## 모듈 개요
- `run.py` CLI 진입점 / `tools.py` collect·render·retrim 오케스트레이션
- `fetch.py` yt-dlp 다운로드 / `transcribe.py` VTT→transcript / `derive.py` cut 적용
- `trim.py` ffmpeg 트림 / `build_ppt.py` PPTX 렌더 / `autoplay.py` 음성 포함 자동재생 덱 / `paths.py` cwd·.work·.history 경로
- `schema.py` 검증 / `ffmpeg_bin.py` ffmpeg / `timeutil.py` / `logging_setup.py` / `doctor.py`
