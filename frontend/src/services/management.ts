import { api } from "@/lib/api"

export interface SyncStatus {
  phase: "idle" | "collecting" | "extracting" | "importing" | "done" | "error"
  progress: number
  total: number
  error: string | null
}

export interface Integration {
  id: number
  name: string
  api_id: string
  channel_name: string
  phone: string | null
  is_active: boolean
  course_id: number | null
  created_at: string
  sync_status: SyncStatus | null
}

export interface IntegrationIn {
  name: string
  channel_name: string
  course_id?: number
  auto_sync?: boolean
}

export interface SystemHealth {
  postgres: boolean
  seaweed: boolean
  storage_used_gb: number
  storage_total_gb: number
}

export const managementService = {
  getIntegrations: () => api.get<Integration[]>("/management/integrations"),
  createIntegration: (data: IntegrationIn) => api.post<Integration>("/management/integrations", data),
  deleteIntegration: (id: number) => api.delete<void>(`/management/integrations/${id}`),
  syncIntegration: (id: number) => api.post<{message: string}>(`/management/integrations/${id}/sync`),
  syncAll: () => api.post<{message: string, integration_ids: number[]}>("/management/integrations/sync-all"),
  getSyncStatus: (id: number) => api.get<SyncStatus>(`/management/integrations/${id}/sync/status`),
  getSystemHealth: () => api.get<SystemHealth>("/management/system/health"),
  telegramSendCode: () =>
    api.post<{ detail: string }>("/management/telegram/send-code", {}),
  telegramVerifyCode: (code: string) =>
    api.post<{ detail: string }>("/management/telegram/verify-code", { code }),
}
