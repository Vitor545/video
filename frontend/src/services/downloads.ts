import { api } from "@/lib/api"

export interface DownloadJob {
  id: number
  video_id: number
  status: "pending" | "downloading" | "done" | "failed" | "retry_pending"
  attempts: number
  error: string | null
  video_title: string | null
  fcode: string | null
  duration_seconds: number | null
  course_id: number | null
  course_title: string | null
  module_name: string | null
  file_size: number | null
  finished_at: string | null
}

export interface QueueStatus {
  queued: number
  active: Record<string, { progress_bytes: number, total_bytes: number }>
}

export interface StatusResponse {
  worker: QueueStatus
  jobs: DownloadJob[]
}

export const downloadsService = {
  enqueueBatch: (videoIds: number[]) => api.post<{ queued_count: number }>("/downloads/batch", { video_ids: videoIds }),
  retryJob: (jobId: number) => api.post(`/downloads/jobs/${jobId}/retry`),
  status: () => api.get<StatusResponse>("/downloads/status"),
  deleteVideoStorage: (videoId: number) => api.delete(`/downloads/videos/${videoId}/storage`),
  deleteCourseStorage: (courseId: number) => api.delete(`/downloads/courses/${courseId}/storage`),
}
