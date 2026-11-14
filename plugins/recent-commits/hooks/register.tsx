import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Changes, Commit, Log } from '../types'

const log = atom({ plugin: 'recent-commits', key: 'log' } as const, null)
/** 미커밋 파일 목록을 펼쳤는지 */
const isOpen = atom({ plugin: 'recent-commits', key: 'isOpen' } as const, false)

const COUNT = 3
/** 폴더별 요약에 보여 줄 폴더 수. 나머지는 `외 N곳` 으로 묶는다. */
const FOLDERS = 4
const TAB = '\t'
const ROOT = '(루트)'
/** 목록에 담아 둘 최대 항목 수 */
const FILES = 100

async function git($: EngineInterface, args: string[]) {
  return $.process.run(['git', ...args], { timeoutMs: 5000 }).catch(() => undefined)
}

/** `git status --porcelain -z` 출력을 종류별·최상위 폴더별 개수로 센다. */
function summarize(porcelain: string): Changes {
  const changes: Changes = { modified: 0, added: 0, deleted: 0, folders: [], files: [] }
  const counts = new Map<string, number>()
  const entries = porcelain.split('\0')

  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i] ?? ''
    if (entry.length < 4) continue
    const code = entry.slice(0, 2)
    const path = entry.slice(3)
    // 이름 변경·복사는 원래 경로가 다음 항목으로 따라온다.
    if (code.includes('R') || code.includes('C')) i += 1

    const kind = code === '??' || code.includes('A') ? 'A' : code.includes('D') ? 'D' : 'M'
    if (kind === 'A') changes.added += 1
    else if (kind === 'D') changes.deleted += 1
    else changes.modified += 1
    if (changes.files.length < FILES) changes.files.push({ kind, path })

    const cut = path.indexOf('/')
    // 최상위 폴더 자체가 새 폴더면 경로가 `폴더/` 로 끝난다.
    const name = cut < 0 ? ROOT : `${path.slice(0, cut)}/`
    counts.set(name, (counts.get(name) ?? 0) + 1)
  }

  changes.folders = [...counts]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))

  return changes
}

async function load($: EngineInterface): Promise<Log | null> {
  const [status, history] = await Promise.all([
    git($, ['-c', 'core.quotepath=false', 'status', '--porcelain', '-z']),
    git($, ['log', '-n', String(COUNT), `--pretty=format:%h${TAB}%ct${TAB}%s`]),
  ])
  // 저장소가 아니면 줄을 그리지 않는다.
  if (!status || status.exitCode !== 0) return null

  // 커밋이 아직 없는 저장소에서는 log 가 실패하므로 빈 목록으로 둔다.
  const commits: Commit[] =
    history && history.exitCode === 0
      ? history.stdout
          .split('\n')
          .map(line => line.split(TAB))
          .filter(cells => cells.length >= 3)
          .map(([hash, at, ...subject]) => ({
            hash: hash ?? '',
            at: Number(at),
            subject: subject.join(TAB),
          }))
      : []

  return { commits, changes: summarize(status.stdout), readAt: await $.clock.now() }
}

async function refresh($: EngineInterface) {
  const next = await load($)
  await update($, log, () => next)
}

const two = (n: number) => String(n).padStart(2, '0')

/** 커밋 시각을 `MM-DD HH:mm` 로 적는다. 올해가 아니면 연도를 앞에 붙인다. */
function stamp(seconds: number, nowMs: number) {
  const d = new Date(seconds * 1000)
  const year = d.getFullYear() === new Date(nowMs).getFullYear() ? '' : `${d.getFullYear()}-`
  return `${year}${two(d.getMonth() + 1)}-${two(d.getDate())} ${two(d.getHours())}:${two(d.getMinutes())}`
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'commits-refresh',
      description: '미커밋 요약과 최근 커밋 줄을 다시 조회한다',
    })
    void refresh($).catch(() => {})

    return next(e)
  })

  on('command.run', { command: 'commits-refresh' }, async $ => {
    await refresh($)
    const now = await read($, log)
    if (now === null) return { text: 'git 저장소가 아닙니다.' }
    const total = now.changes.modified + now.changes.added + now.changes.deleted

    return { text: `미커밋 ${total}개, 최근 커밋 ${now.commits.length}개를 다시 읽었습니다.` }
  })

  // 파일 수정도 미커밋 수를 바꾸므로 턴이 끝날 때마다 다시 읽는다.
  on('turn.complete', async ($, e, next) => {
    void refresh($).catch(() => {})

    return next(e)
  })

  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    const ran = await next(e)
    if (/\bgit\b/.test(e.command)) void refresh($).catch(() => {})

    return ran
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const now = await read($, log)
    // 미커밋 요약이 없던 이전 버전이 남긴 값이면 다음 조회까지 그리지 않는다.
    if (e.props.hasSurvey || now === null || !now.changes?.files) {
      return next(e)
    }

    const { Box, Button, Text } = $.ui.resolve(e)
    const { modified, added, deleted, folders, files } = now.changes
    const open = await read($, isOpen)
    const COLORS = { M: 'yellow', A: 'green', D: 'red' } as const
    const MARKS = { M: '수정', A: '추가', D: '삭제' } as const
    const total = modified + added + deleted
    const shown = folders.slice(0, FOLDERS)
    const rest = folders.length - shown.length

    return (
      <Box flexDirection="column">
        {total === 0 ? (
          <Text dimColor>미커밋 없음</Text>
        ) : (
          <Box>
            <Text bold>미커밋 {total} </Text>
            {modified > 0 ? <Text color="yellow">수정 {modified} </Text> : null}
            {added > 0 ? <Text color="green">새 파일 {added} </Text> : null}
            {deleted > 0 ? <Text color="red">삭제 {deleted} </Text> : null}
            <Text dimColor>│ </Text>
            {shown.map(one => (
              <Text>
                {one.name} {one.count}{'  '}
              </Text>
            ))}
            {rest > 0 ? <Text dimColor>외 {rest}곳 </Text> : null}
            <Button
              key="files"
              label={open ? '목록 접기' : '목록 보기'}
              onPress={() => update($, isOpen, value => !value)}
            />
          </Box>
        )}
        {open && total > 0
          ? files.map(one => (
              <Box>
                <Text color={COLORS[one.kind]}>  {MARKS[one.kind]} </Text>
                <Text wrap="truncate-end">{one.path}</Text>
              </Box>
            ))
          : null}
        {open && total > files.length ? <Text dimColor>  외 {total - files.length}개</Text> : null}
        {now.commits.map(one => (
          <Box>
            <Text dimColor>{stamp(one.at, now.readAt)} </Text>
            <Text color="yellow">{one.hash} </Text>
            <Text wrap="truncate-end">{one.subject}</Text>
          </Box>
        ))}
      </Box>
    )
  })
}
