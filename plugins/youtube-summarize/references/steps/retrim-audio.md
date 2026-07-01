---
name: retrim-audio
description: 렌더가 끝난 뒤 사용자가 컷(트림)을 조정 요청할 때 읽는다. 예 - "앞 5초 더 잘라줘", "인트로 1:10까지로", "뒤를 더 남겨줘". 원본에서 재트림하고 덮어쓰기 전 백업한다.
---

# 오디오 재트림 (retrim-audio)

렌더가 끝난 뒤 사용자가 컷을 다시 잡아달라고 할 때만 사용한다. **재수집·재분석은 하지 않는다.**

## 동작
- **보존된 원본** `.work/audio.source.mp3` 에서 새 좌표로 다시 자른다 → 반복해도 무손실.
- **덮어쓰기 전** 기존 최종물(`slides.pptx` + `audio.trimmed.mp3`)을 `.history/<stamp>/` 에 자동 백업.
- 트림 MP3 + PPT를 재생성해 최종물을 덮어쓴다.

## 명령
```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python -m pipeline.run retrim <video-id> --coords <original|edited> [옵션]
```
- `--coords edited` : 현재 편집본 기준으로 조정 (예: "앞 5초 더" → `--front 5`)
- `--coords original` : 원본 절대초 기준 (예: "원본 1:10까지 인트로" → `--intro 70`)
- 옵션: `--intro <초>` `--outro <초>` `--front <초>` `--back <초>`

예) "앞 5초 더 잘라": `--coords edited --front 5`

→ 반환 `{"pptx_path","mp3_path","backup_dir","backed_up","cut"}`. `backup_dir`(백업 위치)와 새 `cut`을 사용자에게 안내한다.
