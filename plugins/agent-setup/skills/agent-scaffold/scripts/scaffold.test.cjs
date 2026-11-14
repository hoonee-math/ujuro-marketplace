// 실행: node --test "plugins/agent-setup/**/*.test.cjs"
const { test } = require('node:test')
const assert = require('node:assert')
const fs = require('fs')
const os = require('os')
const path = require('path')
const { scaffold, BLOCK_START, BLOCK_END } = require('./scaffold.cjs')

const NOW = new Date('2026-11-14T12:00:00Z').getTime()

function workdir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'scaffold-test-'))
}

const exists = (dir, file) => fs.existsSync(path.join(dir, file))
const read = (dir, file) => fs.readFileSync(path.join(dir, file), 'utf8')

test('에이전트를 하나만 골라도 공통 지침 파일 두 개를 만든다', () => {
  for (const agent of ['claude', 'codex']) {
    const dir = workdir()
    scaffold({ dir, agents: [agent], now: NOW })
    assert.match(read(dir, 'AGENTS.md'), new RegExp(`^# ${path.basename(dir)}`))
    assert.strictEqual(read(dir, 'CLAUDE.md'), '@AGENTS.md\n')
    fs.rmSync(dir, { recursive: true })
  }
})

test('고른 에이전트의 파일만 만든다', () => {
  const dir = workdir()
  scaffold({ dir, agents: ['claude'], now: NOW })
  assert.ok(exists(dir, '.claude/settings.json'))
  assert.ok(exists(dir, '.claude/skills/.gitkeep'))
  assert.ok(exists(dir, '.mcp.json'))
  assert.ok(!exists(dir, '.claude/commands'))
  assert.ok(!exists(dir, '.codex/config.toml'))
  assert.ok(!exists(dir, '.gitignore'))
  JSON.parse(read(dir, '.claude/settings.json'))
  JSON.parse(read(dir, '.mcp.json'))
  fs.rmSync(dir, { recursive: true })
})

test('주석에 기준일을 채워 넣는다', () => {
  const dir = workdir()
  scaffold({ dir, agents: ['codex'], now: NOW })
  const config = read(dir, '.codex/config.toml')
  assert.match(config, /# 기준: \d{4}-\d{2}-\d{2} 공식 문서/)
  assert.doesNotMatch(config, /\{\{/)
  fs.rmSync(dir, { recursive: true })
})

test('이미 있는 파일은 덮어쓰지 않는다', () => {
  const dir = workdir()
  fs.writeFileSync(path.join(dir, 'AGENTS.md'), '기존 내용\n')
  const { results } = scaffold({ dir, agents: ['claude'], now: NOW })
  assert.strictEqual(read(dir, 'AGENTS.md'), '기존 내용\n')
  assert.match(results.find(one => one.path === 'AGENTS.md').status, /건너뜀/)
  fs.rmSync(dir, { recursive: true })
})

test('.gitignore 가 없으면 만들고, 있으면 끝에 덧붙인다', () => {
  const fresh = workdir()
  scaffold({ dir: fresh, agents: ['claude', 'codex'], gitignore: true, now: NOW })
  const created = read(fresh, '.gitignore')
  assert.ok(created.startsWith(BLOCK_START))
  assert.match(created, /CLAUDE\.local\.md/)
  assert.match(created, /\.agents\/skills\/\*/)
  assert.match(created, /^\.env$/m)

  const used = workdir()
  fs.writeFileSync(path.join(used, '.gitignore'), 'node_modules/\ndist/\n')
  scaffold({ dir: used, agents: ['claude'], gitignore: true, now: NOW })
  const appended = read(used, '.gitignore')
  assert.ok(appended.startsWith('node_modules/\ndist/\n\n' + BLOCK_START))
  assert.ok(appended.trimEnd().endsWith(BLOCK_END))
  assert.doesNotMatch(appended, /\.agents\/skills/)

  fs.rmSync(fresh, { recursive: true })
  fs.rmSync(used, { recursive: true })
})

test('다시 실행해도 .gitignore 블록이 두 번 붙지 않고, 에이전트를 더하면 블록만 갱신된다', () => {
  const dir = workdir()
  fs.writeFileSync(path.join(dir, '.gitignore'), 'node_modules/\n')
  scaffold({ dir, agents: ['claude'], gitignore: true, now: NOW })
  const once = read(dir, '.gitignore')
  const again = scaffold({ dir, agents: ['claude'], gitignore: true, now: NOW })
  assert.strictEqual(read(dir, '.gitignore'), once)
  assert.strictEqual(again.results.find(one => one.path === '.gitignore').status, '변경 없음')

  scaffold({ dir, agents: ['claude', 'codex'], gitignore: true, now: NOW })
  const widened = read(dir, '.gitignore')
  assert.strictEqual(widened.split(BLOCK_START).length - 1, 1)
  assert.match(widened, /\.agents\/skills\/\*/)
  assert.ok(widened.startsWith('node_modules/\n'))
  fs.rmSync(dir, { recursive: true })
})

test('미리 보기는 아무것도 만들지 않는다', () => {
  const dir = workdir()
  const { results } = scaffold({ dir, agents: ['claude'], gitignore: true, dryRun: true, now: NOW })
  assert.deepStrictEqual(fs.readdirSync(dir), [])
  assert.ok(results.length > 0)
  fs.rmSync(dir, { recursive: true })
})

test('기준일이 오래된 템플릿을 알려 준다', () => {
  const dir = workdir()
  const later = NOW + 200 * 86400000
  assert.strictEqual(scaffold({ dir, agents: ['claude'], dryRun: true, now: NOW }).stale.length, 0)
  assert.ok(scaffold({ dir, agents: ['claude'], dryRun: true, now: later }).stale.length > 0)
  fs.rmSync(dir, { recursive: true })
})

test('없는 에이전트 이름은 오류로 알린다', () => {
  const dir = workdir()
  assert.throws(() => scaffold({ dir, agents: ['nope'], now: NOW }), /알 수 없는 에이전트/)
  fs.rmSync(dir, { recursive: true })
})
