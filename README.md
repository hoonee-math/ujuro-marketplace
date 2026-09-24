# ujuro-marketplace

hoonee-math(최광훈)의 개인 Claude Code 플러그인 마켓플레이스입니다.
개인 GitHub repo 하나로 어디서든 플러그인을 설치하고 친구와 공유할 수 있습니다.

## 설치 방법

```bash
# 1) 마켓플레이스 등록 (GitHub owner/repo 축약)
/plugin marketplace add hoonee-math/ujuro-marketplace

# 2) 플러그인 설치
/plugin install hello-ujuro@ujuro
```

> `add`는 **repo 이름**(`hoonee-math/ujuro-marketplace`)으로,
> `install`은 **마켓플레이스 이름**(`ujuro`, `marketplace.json`의 `name`)으로 합니다.

설치 후:
- `/hello` — 제작자 소개 슬래시 커맨드
- "ujuro 만든 사람 누구야?" 처럼 물으면 `ujuro-greeting` 스킬이 자동 발동

## 수록 플러그인

| 플러그인 | 설명 | 구성 |
|----------|------|------|
| `hello-ujuro` | ujuro 마켓플레이스 / 제작자 소개 | 슬래시 커맨드 `/hello` + 스킬 `ujuro-greeting` |

## 저장소 구조

```
.
├── .claude-plugin/
│   └── marketplace.json            # 마켓플레이스 정의 (name: ujuro)
└── plugins/
    └── hello-ujuro/                # 예시 플러그인
        ├── .claude-plugin/
        │   └── plugin.json         # 플러그인 매니페스트
        ├── commands/
        │   └── hello.md            # /hello 슬래시 커맨드
        └── skills/
            └── ujuro-greeting/
                └── SKILL.md        # 자동 발동 스킬
```

## 새 플러그인 추가하기

1. `plugins/<플러그인이름>/` 폴더 생성
2. 필요한 구성 추가 — `commands/*.md`, `skills/<이름>/SKILL.md`, `agents/*.md`, `hooks/hooks.json`, `.mcp.json` 등
3. (선택) `plugins/<플러그인이름>/.claude-plugin/plugin.json` 매니페스트 작성
4. 루트 `.claude-plugin/marketplace.json`의 `plugins` 배열에 한 항목 추가
5. 커밋 & push → 사용자는 `/plugin marketplace update ujuro` 후 새 플러그인 설치

> 구조·구성요소(커맨드/스킬/에이전트/훅/MCP) 요약과 최소 예시는 [docs/plugin-authoring.md](./docs/plugin-authoring.md) 참고.

## 로컬에서 검증

```bash
# 로컬 경로로 등록해 먼저 확인
/plugin marketplace add ./
/plugin install hello-ujuro@ujuro
```

## 제작자

**최광훈 (hoonee-math)** — 수학과 우주를 좋아하는 AI 개발자
에이엔제이솔루션 Ai-Ops 팀
