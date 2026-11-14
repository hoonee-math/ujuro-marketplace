export type Commit = {
  hash: string
  subject: string
  /** 커밋 시각 (epoch 초) */
  at: number
}

/** 미커밋 항목 요약. 새 폴더는 git 이 한 항목으로 묶어 보고한다. */
export type Changes = {
  modified: number
  added: number
  deleted: number
  /** 최상위 폴더별 항목 수, 많은 순 */
  folders: { name: string; count: number }[]
  /** 항목 목록 (최대 100개). kind 는 M 수정, A 새 파일, D 삭제 */
  files: { kind: 'M' | 'A' | 'D'; path: string }[]
}

export type Log = {
  commits: Commit[]
  changes: Changes
  /** 조회 시각 (epoch ms) */
  readAt: number
}

declare module 'claude-code' {
  interface PluginState {
    'recent-commits': { log: Log | null; isOpen: boolean }
  }
}
