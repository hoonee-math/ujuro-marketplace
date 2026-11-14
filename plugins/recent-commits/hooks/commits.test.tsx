import { expect, test } from 'claude-code/testing'

const BAND = {
  plugin: 'recent-commits',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isCollapsed: false,
    isWorking: false,
    maxRows: 10,
    bodyColumns: 120,
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

const NOW = 1763100000
const ran = (exitCode: number, stdout: string) => ({
  value: { exitCode, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
})

// 수정 2(.gitignore, src/a.ts), 새 항목 3(새 폴더 docs/, src/b.ts, 이름 변경된 src/new.ts 는 수정으로 셈), 삭제 1
const STATUS = [
  ' M .gitignore',
  ' M src/a.ts',
  '?? docs/',
  '?? src/b.ts',
  'R  src/new.ts',
  'src/old.ts',
  ' D lib/gone.ts',
  '',
].join('\0')

function answers(status: ReturnType<typeof ran>, history: ReturnType<typeof ran>) {
  return (_$: unknown, e: { argv: readonly string[] }) =>
    e.argv.includes('status') ? status : history
}

test('미커밋 요약과 최근 커밋을 그린다', async ($, on) => {
  on('command.register', () => ({ value: { command: 'commits-refresh' } }))
  on('clock.now', () => ({ value: NOW * 1000 }))
  on(
    'process.run',
    answers(ran(0, STATUS), ran(0, `abc1234\t${NOW - 7200}\tfeat(x): 첫째`)),
  )

  await $.command.run({ command: 'commits-refresh' } as never)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })

  expect(await ui.find({ type: 'Text', text: /미커밋 6/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /수정 3/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /새 파일 2/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /삭제 1/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /src\/ 3/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /docs\/ 1/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /\(루트\) 1/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /abc1234/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /feat\(x\): 첫째/ })).toBeTruthy()

  // 목록은 접힌 채로 시작하고, 버튼을 누르면 파일이 보인다.
  expect(await ui.find({ type: 'Text', text: /src\/a\.ts/ })).toBeUndefined()
  await ui.press({ key: 'files' })
  expect(await ui.find({ type: 'Text', text: /src\/a\.ts/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /lib\/gone\.ts/ })).toBeTruthy()
  await ui.unmount()
})

test('변경이 없으면 미커밋 없음으로 그린다', async ($, on) => {
  on('command.register', () => ({ value: { command: 'commits-refresh' } }))
  on('clock.now', () => ({ value: NOW * 1000 }))
  on('process.run', answers(ran(0, ''), ran(0, `abc1234\t${NOW}\tinit`)))

  await $.command.run({ command: 'commits-refresh' } as never)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })

  expect(await ui.find({ type: 'Text', text: /미커밋 없음/ })).toBeTruthy()
  await ui.unmount()
})

test('커밋이 없는 새 저장소에서도 미커밋 요약은 그린다', async ($, on) => {
  on('command.register', () => ({ value: { command: 'commits-refresh' } }))
  on('clock.now', () => ({ value: NOW * 1000 }))
  on('process.run', answers(ran(0, '?? a.txt\0'), ran(128, '')))

  await $.command.run({ command: 'commits-refresh' } as never)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })

  expect(await ui.find({ type: 'Text', text: /미커밋 1/ })).toBeTruthy()
  await ui.unmount()
})

test('git 저장소가 아니면 아무것도 그리지 않는다', async ($, on) => {
  on('command.register', () => ({ value: { command: 'commits-refresh' } }))
  on('process.run', () => ran(128, ''))

  await $.command.run({ command: 'commits-refresh' } as never)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })

  expect(await ui.find({ type: 'Text' })).toBeUndefined()
  await ui.unmount()
})
