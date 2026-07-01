---
name: english-conversation
description: 영어 회화연습 영상(다양한 표현/패턴을 예문 반복으로 학습)의 덱 구성 지침. 영상 모드에서 유형이 english_conversation일 때, 또는 자료 모드에서 이 포맷으로 analysis.json을 작성할 때 읽는다.
---

# 영어 회화연습 (english-conversation) 덱 지침

`transcript.json`(자막 de-roll 큐: start·text)과 `info.json`(제목·설명·챕터)을 근거로
`analysis.json` 을 `.work/analysis.json` 에 작성한다. 정답 구조는 없으니 영상에 맞게 판단한다.

## 공통 규칙
- 모든 row는 `primary`(영어/주내용) + `secondary`(한글/부가, 선택)로 **일관**되게. **헤더도 예외 없음**(괄호 안 번역 금지).
- de-roll로 조각난 영어는 **완결 문장**으로 재구성하고, ASR 오타는 교정한다.

## 덱 구성
패턴마다:
- 헤더: `{"kind":"header","label":"1","t_seconds":<패턴 시작초>,"primary":"<영어 템플릿>","secondary":"<한국어 뜻>"}`
- 예문들: `{"kind":"line","primary":"<영어 문장>","secondary":"<한글 번역>"}` (예문엔 **번호·시간 없음**)

## cut (트림)
`{"intro_end":<본격 내용 시작초>, "outro_start":<마무리/홍보 시작초>}`.
모든 `t_seconds` 는 **원본 오디오 기준**.

## analysis.json 계약
`.work/analysis.json` 에 아래를 Write. (`source` 는 렌더 스크립트가 info.json에서 채우니 생략)
```json
{
  "type": "english_study",
  "cut": { "intro_end": 22.0, "outro_start": 717.7 },
  "deck": {
    "subtitle": "54개 패턴 · 105문장",
    "rows": [
      {"kind":"header","label":"1","t_seconds":24.0,"primary":"I'm really into","secondary":"~에 빠져 있어"},
      {"kind":"line","primary":"I'm really into this drama lately.","secondary":"나 요즘 이 드라마 완전 빠져 있어."}
    ]
  }
}
```

작성 후 SKILL.md 4)단계(render)로 진행한다.
