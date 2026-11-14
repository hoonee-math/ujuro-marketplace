// 실행: node --test plugins/agent-setup/hooks
const { test } = require('node:test')
const assert = require('node:assert')
const { runsGitInit } = require('./git-init-guide.cjs')

const RUNS = [
  'git init',
  'git init -b main',
  'cd foo && git init',
  'git -C sub init',
  'git -c init.defaultBranch=main init',
  'git --git-dir=x/.git init',
  'mkdir a; git init a',
  'GIT_TRACE=1 git init',
  'git.exe init',
  'git -C "my dir" init',
]

const DOES_NOT_RUN = [
  'git status',
  'npm init -y',
  'echo "git init"',
  "echo 'git init'",
  'echo git init',
  ': git init',
  'git commit -m "git init 훅 추가"',
  "git commit -m 'run git init first'",
  'git commit -q -F - <<\'EOF\'\nfeat: git init 때 안내\n\n- git init 을 감지한다\nEOF\ngit log -1',
  'ls # git init',
  'git submodule init',
  'git config init.defaultBranch main',
  'grep -rn "git init" docs',
  '',
]

for (const command of RUNS) {
  test(`잡는다: ${command}`, () => assert.strictEqual(runsGitInit(command), true))
}

for (const command of DOES_NOT_RUN) {
  test(`잡지 않는다: ${command.split('\n')[0] || '(빈 명령)'}`, () =>
    assert.strictEqual(runsGitInit(command), false))
}
