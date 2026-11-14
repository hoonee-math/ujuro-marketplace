#!/usr/bin/env node
// 프로젝트 폴더에 코딩 에이전트 설정 뼈대를 만든다.
// 에이전트별 내용은 ../templates/<이름>/template.json 이 정한다. 에이전트를 추가할 때는 템플릿 폴더만 더하면 된다.
const fs = require('fs')
const path = require('path')

const TEMPLATES = path.join(__dirname, '..', 'templates')
const COMMON = 'common'
const BLOCK_START = '# >>> agent-setup (이 블록은 scaffold 스크립트가 관리한다)'
const BLOCK_END = '# <<< agent-setup'

function loadTemplate(name) {
  const file = path.join(TEMPLATES, name, 'template.json')
  if (!fs.existsSync(file)) return undefined
  return { ...JSON.parse(fs.readFileSync(file, 'utf8')), dir: path.dirname(file) }
}

function available() {
  return fs
    .readdirSync(TEMPLATES, { withFileTypes: true })
    .filter(entry => entry.isDirectory() && entry.name !== COMMON)
    .map(entry => entry.name)
    .sort()
}

function fill(text, values) {
  return text.replace(/\{\{(\w+)\}\}/g, (whole, key) => values[key] ?? whole)
}

/** 템플릿들의 제외 규칙을 표식 사이의 한 블록으로 묶는다. */
function gitignoreBlock(templates) {
  const lines = [BLOCK_START]
  for (const template of templates) {
    if (!template.gitignore?.length) continue
    lines.push(...template.gitignore, '')
  }
  if (lines.at(-1) === '') lines.pop()
  lines.push(BLOCK_END)
  return lines.join('\n')
}

/** 이미 블록이 있으면 그 자리에서 바꾸고, 없으면 파일 끝에 덧붙인다. */
function mergeGitignore(existing, block) {
  const start = existing.indexOf(BLOCK_START)
  const end = existing.indexOf(BLOCK_END)
  if (start >= 0 && end > start) {
    return existing.slice(0, start) + block + existing.slice(end + BLOCK_END.length)
  }
  if (existing.trim() === '') return `${block}\n`
  return `${existing.replace(/\s*$/, '')}\n\n${block}\n`
}

/**
 * @param {{ dir: string, agents: string[], gitignore?: boolean, dryRun?: boolean }} options
 * @returns {{ results: object[], templates: object[] }}
 */
function scaffold({ dir, agents, gitignore = false, dryRun = false }) {
  const names = [COMMON, ...new Set(agents)]
  const templates = names.map(name => {
    const template = loadTemplate(name)
    if (!template) {
      throw new Error(`알 수 없는 에이전트: ${name} (사용 가능: ${available().join(', ')})`)
    }
    return template
  })

  const target = path.resolve(dir)
  const values = { project: path.basename(target) }
  const results = []

  for (const template of templates) {
    for (const file of template.files) {
      const destination = path.join(target, file.path)
      const result = { ...file, agent: template.name }
      if (fs.existsSync(destination)) {
        results.push({ ...result, status: '건너뜀(이미 있음)' })
        continue
      }
      if (!dryRun) {
        fs.mkdirSync(path.dirname(destination), { recursive: true })
        const content = file.from
          ? fill(fs.readFileSync(path.join(template.dir, file.from), 'utf8'), values)
          : ''
        fs.writeFileSync(destination, content)
      }
      results.push({ ...result, status: '만듦' })
    }
  }

  if (gitignore) {
    const destination = path.join(target, '.gitignore')
    const existing = fs.existsSync(destination) ? fs.readFileSync(destination, 'utf8') : ''
    const merged = mergeGitignore(existing, gitignoreBlock(templates))
    const status =
      existing === '' ? '만듦' : merged === existing ? '변경 없음' : '끝에 추가 또는 블록 갱신'
    if (!dryRun && merged !== existing) fs.writeFileSync(destination, merged)
    results.push({
      path: '.gitignore',
      agent: '공통',
      description: '개인 설정·비밀 값·스킬 본체 제외 규칙',
      doc: 'https://git-scm.com/docs/gitignore',
      status,
    })
  }

  return { results, templates }
}

function printList() {
  console.log('사용할 수 있는 에이전트:')
  for (const name of available()) {
    console.log(`  ${name} — ${loadTemplate(name).title}`)
  }
}

function main(argv) {
  const options = { dir: process.cwd(), agents: [], gitignore: false, dryRun: false }
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]
    if (arg === '--dir') options.dir = argv[++i]
    else if (arg === '--gitignore') options.gitignore = true
    else if (arg === '--dry-run') options.dryRun = true
    else if (arg === '--list') return printList()
    else if (arg === '--help' || arg === '-h') {
      console.log('사용법: node scaffold.cjs [--dir <폴더>] [--gitignore] [--dry-run] <에이전트>...')
      console.log('        node scaffold.cjs --list')
      return
    } else if (arg.startsWith('-')) throw new Error(`알 수 없는 옵션: ${arg}`)
    else options.agents.push(arg)
  }

  const { results } = scaffold(options)

  console.log(`${options.dryRun ? '[미리 보기] ' : ''}대상 폴더: ${path.resolve(options.dir)}`)
  for (const result of results) {
    console.log(`  ${result.status}  ${result.path}`)
    console.log(`      ${result.description} — ${result.doc}`)
    for (const one of result.keys ?? []) {
      console.log(`        ${one.key}: ${one.description} — ${one.doc}`)
    }
  }
  console.log('\n위 설명은 템플릿에 적힌 것이다. 커밋 전에 공식 문서와 대조한다.')
}

module.exports = { scaffold, mergeGitignore, gitignoreBlock, available, BLOCK_START, BLOCK_END }

if (require.main === module) {
  try {
    main(process.argv.slice(2))
  } catch (error) {
    console.error(error.message)
    process.exit(1)
  }
}
