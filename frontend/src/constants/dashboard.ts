import type { ChartConfig } from "@/components/ui/chart"

export const STATS = [
  { label: "Cursos Ativos", value: "2", unit: "cursos" },
  { label: "Aulas Assistidas", value: "312", unit: "de 1113" },
  { label: "Horas Estudadas", value: "48h", unit: "este mês" },
  { label: "Em Download", value: "3", unit: "na fila" },
]

export const WEEKLY_DATA = [
  { week: "Sem 1", hours: 3.5, goal: 5 },
  { week: "Sem 2", hours: 6.2, goal: 5 },
  { week: "Sem 3", hours: 4.8, goal: 5 },
  { week: "Sem 4", hours: 7.1, goal: 5 },
  { week: "Sem 5", hours: 2.3, goal: 5 },
  { week: "Sem 6", hours: 8.4, goal: 5 },
  { week: "Sem 7", hours: 5.9, goal: 5 },
  { week: "Sem 8", hours: 4.2, goal: 5 },
]

export type RadialDatum = { name: string; value: number; fill: string }

export const RADIAL_DATA: RadialDatum[] = [
  { name: "Actions", value: 0,   fill: "#1e3a5f" },
  { name: "K8s",     value: 12,  fill: "#1d4ed8" },
  { name: "Docker",  value: 68,  fill: "#2563eb" },
  { name: "Git",     value: 95,  fill: "#60a5fa" },
  { name: "Linux",   value: 100, fill: "#93c5fd" },
]

export const STREAK_DATA = [
  { day: "Seg", min: 45 }, { day: "Ter", min: 90 }, { day: "Qua", min: 30 },
  { day: "Qui", min: 120 }, { day: "Sex", min: 75 }, { day: "Sáb", min: 0 },
  { day: "Dom", min: 60 },
]

export const HOURLY_DATA = [
  { hour: "6h", min: 0 },   { hour: "8h", min: 30 },
  { hour: "10h", min: 90 }, { hour: "12h", min: 45 },
  { hour: "14h", min: 120 },{ hour: "16h", min: 200 },
  { hour: "18h", min: 240 },{ hour: "20h", min: 180 },
  { hour: "22h", min: 60 },
]

export const RECENT_VIDEOS = [
  { id: 1, fcode: "F0217", title: "Orquestração de Containers e Kubernetes", module: "Kubernetes 2.0", duration: "11:33", progress: 72 },
  { id: 2, fcode: "F0198", title: "Docker Compose Avançado", module: "Docker 2.0", duration: "14:20", progress: 100 },
  { id: 3, fcode: "F0185", title: "Volumes e Redes no Docker", module: "Docker 2.0", duration: "09:45", progress: 45 },
  { id: 4, fcode: "F0038", title: "GitHub Actions — CI/CD Pipeline", module: "Git e GitHub", duration: "18:02", progress: 100 },
]

export const MY_COURSES = [
  { id: 1, title: "DevOps Pro 2",    modules: 5, lessons: 1113, hours: 160, progress: 28 },
  { id: 2, title: "SRE Foundations", modules: 4, lessons: 340,  hours: 48,  progress: 5 },
]

export const WEEKLY_CONFIG = {
  hours: { label: "Horas estudadas", color: "#3b82f6" },
  goal:  { label: "Meta semanal",    color: "#374151" },
} satisfies ChartConfig

export const STREAK_CONFIG = {
  min: { label: "Minutos", color: "#3b82f6" },
} satisfies ChartConfig

export const HOURLY_CONFIG = {
  min: { label: "Minutos", color: "#3b82f6" },
} satisfies ChartConfig

export const RADIAL_CONFIG = {
  value: { label: "Progresso" },
} satisfies ChartConfig
