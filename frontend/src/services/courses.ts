import { api } from "@/lib/api"

export interface Course {
  id: number
  title: string
  description: string | null
  telegram_channel: string
  total_videos: number
  total_duration_seconds: number
  thumbnail_url: string | null
  created_at: string
}

export type DownloadStatus =
  | "pending"
  | "downloading"
  | "done"
  | "failed"
  | "retry_pending"

export interface Video {
  id: number
  course_id?: number
  module_name: string
  title: string
  fcode: string
  media_type?: "video" | "file" | string
  mime_type?: string | null
  original_filename?: string | null
  file_ext?: string | null
  duration_seconds: number
  order_index: number
  download_status: DownloadStatus
  file_size: number | null
  msg_id: number | null
  progress_seconds: number
  completed: boolean
}

export interface Module {
  name: string
  videos: Video[]
  total: number
  done: number
  completed: number
  duration: number
}

export interface CourseDetail {
  course: {
    id: number
    title: string
    description: string | null
    telegram_channel: string
    thumbnail_url: string | null
    total_videos: number
    total_duration_seconds: number
  }
  modules: Module[]
  total_videos: number
  downloaded: number
  completed: number
  progress_pct: number
  download_pct: number
}

export interface CourseIn {
  title: string
  telegram_channel: string
  description?: string
}

export const coursesService = {
  list: () => api.get<Course[]>("/courses/"),
  get: (id: number) => api.get<CourseDetail>(`/courses/${id}`),
  create: (data: CourseIn) => api.post<Course>("/courses/", data),
  listVideos: (id: number) => api.get<Video[]>(`/courses/${id}/videos`),
}
