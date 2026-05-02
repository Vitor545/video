import { api } from "@/lib/api"

export interface VideoProgress {
  video_id: number
  progress_seconds: number
  completed: boolean
}

export interface StreamUrl {
  url: string
  expires_in: number
}

export interface DownloadUrl {
  url: string
  expires_in: number
}

export const videosService = {
  /** Busca a URL presigned (1h TTL). Use o resultado direto no <video src>. */
  getStreamUrl: (id: number) => api.get<StreamUrl>(`/videos/${id}/stream-url`),
  getDownloadUrl: (id: number) => api.get<DownloadUrl>(`/videos/${id}/download-url`),
  getProgress: (id: number) => api.get<VideoProgress>(`/videos/${id}/progress`),
  saveProgress: (id: number, progress_seconds: number, completed = false) =>
    api.post<VideoProgress>(`/videos/${id}/progress`, { progress_seconds, completed }),
}
