import { api } from "@/lib/api"

export interface DashboardStats {
  active_courses: number
  lessons_completed: number
  total_lessons: number
  hours_this_month: number
  queued_downloads: number
  progress_pct?: number
}

export interface WeeklyPoint {
  week_start: string
  label: string
  hours: number
}

export interface StreakPoint {
  day: string
  date: string
  min: number
}

export interface HourlyPoint {
  hour: string
  min: number
}

export interface RecentVideo {
  video_id: number
  course_id: number
  course_title: string
  fcode: string
  title: string
  module_name: string
  duration_seconds: number
  progress_seconds: number
  progress_pct: number
  completed: boolean
  watched_at: string
}

export interface ModuleProgress {
  course_id: number
  course_title: string
  module_name: string
  total: number
  completed: number
  percent: number
}

export interface MyCourse {
  id: number
  title: string
  modules: number
  lessons: number
  hours: number
  completed: number
  progress_pct: number
}

export const dashboardService = {
  stats: (courseId?: number | null) =>
    api.get<DashboardStats>(`/dashboard/stats${courseId ? `?course_id=${courseId}` : ""}`),
  weekly: (weeks = 8, courseId?: number | null) =>
    api.get<WeeklyPoint[]>(
      `/dashboard/weekly?weeks=${weeks}${courseId ? `&course_id=${courseId}` : ""}`
    ),
  streak: (courseId?: number | null) =>
    api.get<StreakPoint[]>(`/dashboard/streak${courseId ? `?course_id=${courseId}` : ""}`),
  hourly: (courseId?: number | null) =>
    api.get<HourlyPoint[]>(`/dashboard/hourly${courseId ? `?course_id=${courseId}` : ""}`),
  recent: (limit = 10) => api.get<RecentVideo[]>(`/dashboard/recent?limit=${limit}`),
  modules: (top = 5, courseId?: number | null) =>
    api.get<ModuleProgress[]>(
      `/dashboard/modules?top=${top}${courseId ? `&course_id=${courseId}` : ""}`
    ),
  myCourses: () => api.get<MyCourse[]>("/dashboard/my-courses"),
}
