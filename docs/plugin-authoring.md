# 플러그인 제작 가이드 (핵심 요약)

ujuro 마켓플레이스에 플러그인을 추가하기 위한 **구조 중심** 요약입니다.
자세한 내용은 맨 아래 [공식 문서 링크](#더-자세히-공식-문서)를 참고하세요.

---

## 1. 마켓플레이스 repo 구조 (현재 프로젝트)

```
ujuro-marketplace/                       # = 이 git repo
├── .claude-plugin/
│   └── marketplace.json                 # 마켓플레이스 정의 (유일한 필수 파일)
└── plugins/
    └── hello-ujuro/                     # 플러그인 1개 = 폴더 1개
        ├── .claude-plugin/
        │   └── plugin.json              # 플러그인 매니페스트 (선택)
        ├── commands/
        │   └── hello.md                 # 슬래시 커맨드
        └── skills/
            └── ujuro-greeting/
                └── SKILL.md             # 스킬
```

- **`.claude-plugin/marketplace.json`** = repo 전체가 마켓플레이스임을 정의. 여기 `plugins` 배열에 플러그인을 등록.
- **플러그인 하나 = `plugins/<이름>/` 폴더 하나.**

---

## 2. 플러그인 안에 넣을 수 있는 것들

폴더 이름은 **관례상 고정**입니다. 필요한 것만 넣으면 됩니다 (전부 선택).

| 종류 | 위치 | 역할 | 호출 방식 |
|------|------|------|-----------|
| **커맨드** | `commands/이름.md` | 슬래시 명령 | 사용자가 직접 `/이름` |
| **스킬** | `skills/이름/SKILL.md` | 상황별 지식·워크플로 | 모델이 자동 발동 |
| **에이전트** | `agents/이름.md` | 서브에이전트 | Task/자동 위임 |
| **훅** | `hooks/hooks.json` | 이벤트 핸들러 | 도구 실행 전후 등 자동 |
| **MCP 서버** | `.mcp.json` | 외부 도구/데이터 연결 | 세션에서 도구로 노출 |
| **매니페스트** | `.claude-plugin/plugin.json` | 이름·버전·작성자 등 메타 | — |

> **중요:** 각 구성은 **서로 독립**입니다. 스킬만 넣어도 커맨드는 안 생기고, 그 반대도 마찬가지.
> 플러그인은 커맨드만 / 스킬만 / 조합 등 원하는 것만 담습니다.

### 커맨드 vs 스킬 한 줄 요약
- **커맨드** = 내가 `/명령` 으로 **직접** 부르는 것.
- **스킬** = `description` 에 적힌 상황이 오면 모델이 **알아서** 부르는 것.

---

## 3. 최소 예시

### commands/hello.md
```markdown
---
description: 인사를 출력합니다
---

사용자에게 "안녕하세요!" 라고 인사하세요.
```

### skills/이름/SKILL.md
```markdown
---
name: my-skill
description: 언제 이 스킬을 써야 하는지 (모델이 이걸 보고 자동 발동 판단)
---

여기에 수행할 작업/지식/절차를 작성.
```

### .claude-plugin/plugin.json (선택)
```json
{
  "name": "my-plugin",
  "description": "이 플러그인 설명",
  "version": "1.0.0",
  "author": { "name": "최광훈 (hoonee-math)" }
}
```

> 훅·MCP의 스크립트 경로는 `${CLAUDE_PLUGIN_ROOT}` 변수로 플러그인 폴더 기준 절대경로를 잡습니다.

---

## 4. 새 플러그인 추가 절차

1. `plugins/<새이름>/` 폴더 생성
2. 필요한 구성 추가 (`commands/`, `skills/`, `agents/`, `hooks/`, `.mcp.json`)
3. (선택) `plugins/<새이름>/.claude-plugin/plugin.json` 작성
4. **`.claude-plugin/marketplace.json` 의 `plugins` 배열에 항목 추가** ← 이걸 빠뜨리면 안 보임
   ```json
   { "name": "새이름", "source": "./plugins/새이름", "version": "1.0.0",
     "description": "설명" }
   ```
5. `git commit` → `git push`
6. 사용자는 `/plugin marketplace update ujuro` 후 `/plugin install 새이름@ujuro`

---

## 더 자세히 (공식 문서)

- 플러그인 만들기: https://code.claude.com/docs/en/plugins.md
- 마켓플레이스: https://code.claude.com/docs/en/plugin-marketplaces.md
- 설치·발견: https://code.claude.com/docs/en/discover-plugins.md
- 설정(settings.json): https://code.claude.com/docs/en/settings.md
