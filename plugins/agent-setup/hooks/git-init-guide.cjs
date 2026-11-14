// PreToolUse 훅: 저장소를 새로 만드는 git 명령을 실행하려 할 때 agent-setup 스킬을 쓰라고 알려 준다. 실행은 막지 않는다.
const fs = require('fs')

/** 값을 따로 받는 git 전역 옵션. 다음 토큰까지 건너뛴다. */
const OPTIONS_WITH_VALUE = new Set(['-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path'])

/**
 * 명령줄에서 실제로 실행되는 `git init` 이 있는지 본다.
 * 따옴표 안의 글자, heredoc 본문, 주석은 실행되는 명령이 아니므로 먼저 지운다.
 */
function runsGitInit(commandLine) {
  const text = String(commandLine)
    .replace(/<<-?\s*(['"]?)(\w+)\1[\s\S]*?\n\s*\2(?=\s|$)/g, ' ')
    .replace(/'[^']*'/g, ' Q ')
    .replace(/"(?:\\.|[^"\\])*"/g, ' Q ')
    .replace(/(^|\s)#[^\n]*/g, ' ')

  return text.split(/&&|\|\||[;|&\n()]/).some(segment => {
    const tokens = segment.trim().split(/\s+/).filter(Boolean)
    // 앞에 붙은 환경 변수 지정(NAME=value)은 건너뛴다.
    while (tokens.length > 0 && /^\w+=/.test(tokens[0])) tokens.shift()
    if (!/^git(\.exe)?$/i.test(tokens[0] ?? '')) return false

    let i = 1
    while (i < tokens.length && tokens[i].startsWith('-')) {
      i += OPTIONS_WITH_VALUE.has(tokens[i]) ? 2 : 1
    }
    return tokens[i] === 'init'
  })
}

module.exports = { runsGitInit }

if (require.main === module) {
  let input = {}
  try {
    input = JSON.parse(fs.readFileSync(0, 'utf8'))
  } catch {}

  if (runsGitInit(input.tool_input?.command ?? '')) {
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
}
