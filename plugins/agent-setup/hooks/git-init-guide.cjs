// PreToolUse 훅: `git init` 을 실행하려 할 때 agent-setup 스킬을 쓰라고 알려 준다. 실행은 막지 않는다.
const fs = require('fs')

let input = {}
try {
  input = JSON.parse(fs.readFileSync(0, 'utf8'))
} catch {}

const command = String(input.tool_input?.command ?? '')

// `git init`, `git -C <dir> init` 처럼 한 명령 안에서 git 뒤에 init 이 오는 경우만 잡는다.
if (/(^|[\s;&|(])git\b[^;&|\n]*\sinit(\s|$)/.test(command)) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        additionalContext:
          '신규 저장소 초기화다. agent-setup 스킬을 불러, 에이전트 설정 중 무엇을 초기화할지 사용자에게 간단히 안내한다.',
      },
    }),
  )
}
