/** 更新渠道：stable 仅稳定版；beta 含预发布版本 */
export type UpdateChannel = 'stable' | 'beta';

/** `GET /api/v1/update/check` 返回体 */
export interface UpdateInfo {
  current: string;
  latest: string | null;
  has_update: boolean;
  channel: UpdateChannel;
  notes: string;
  published_at: string | null;
  is_prerelease: boolean;
  bundle_url: string | null;
  sha256_url: string | null;
  /** 当前已应用的覆盖层版本（无则为 null） */
  applied_version: string | null;
  /** 是否存在可回滚的备份 */
  can_rollback: boolean;
  error: string | null;
}

/** `POST /api/v1/update/apply` 与 `/rollback` 返回体 */
export interface UpdateApplyResult {
  success: boolean;
  message: string;
  version: string | null;
  restart_required: boolean;
}

/** SSE `update` 事件推送的进度负载 */
export interface UpdateProgress {
  phase:
    | 'idle'
    | 'checking'
    | 'downloading'
    | 'verifying'
    | 'unpacking'
    | 'promoting'
    | 'restarting'
    | 'error'
    | 'done';
  percent: number;
  message: string;
  version: string | null;
  restart_required: boolean;
  error: string | null;
}
