import { Clock, BookOpen, CheckCircle2, Download } from "lucide-react"

export const COURSE_DATA = {
  title: "DevOps Pro 2",
  description: "Formação completa em DevOps: Linux, Git/GitHub, Docker, Kubernetes e GitHub Actions.",
  totalHours: 160,
  totalLessons: 1113,
  progress: 28,
  downloaded: 175,
}

export const COURSE_MODULES = [
  {
    id: 1, name: "Linux", lessons: 93, duration: "18h 30min", progress: 100,
    items: [
      { fcode: "F0001", title: "Introdução ao Linux e terminal", dur: "14:20", done: true },
      { fcode: "F0002", title: "Navegação no sistema de arquivos", dur: "11:45", done: true },
      { fcode: "F0003", title: "Permissões e usuários", dur: "16:30", done: true },
      { fcode: "F0004", title: "Gerenciamento de pacotes", dur: "13:00", done: true },
    ],
  },
  {
    id: 2, name: "Git e GitHub", lessons: 20, duration: "6h 00min", progress: 95,
    items: [
      { fcode: "F0101", title: "Introdução ao Git", dur: "12:00", done: true },
      { fcode: "F0102", title: "Branches e merges", dur: "15:30", done: true },
      { fcode: "F0103", title: "Pull Requests e code review", dur: "18:45", done: true },
      { fcode: "F0038", title: "GitHub Actions — CI/CD Pipeline", dur: "18:02", done: false },
    ],
  },
  {
    id: 3, name: "Docker 2.0", lessons: 176, duration: "42h 00min", progress: 68,
    items: [
      { fcode: "F0039", title: "Introdução aos Containers", dur: "12:30", done: true },
      { fcode: "F0057", title: "Build de imagens", dur: "14:10", done: true },
      { fcode: "F0059", title: "Multi-stage build", dur: "16:45", done: false },
      { fcode: "F0081", title: "Bridge network", dur: "13:00", done: false },
    ],
  },
  {
    id: 4, name: "Kubernetes 2.0", lessons: 216, duration: "51h 00min", progress: 12,
    items: [
      { fcode: "F0200", title: "Introdução ao Kubernetes", dur: "15:20", done: true },
      { fcode: "F0201", title: "Pods e Deployments", dur: "18:00", done: true },
      { fcode: "F0218", title: "Services no Kubernetes", dur: "11:33", done: false },
      { fcode: "F0219", title: "ConfigMaps e Secrets", dur: "14:45", done: false },
    ],
  },
  {
    id: 5, name: "GitHub Actions", lessons: 93, duration: "24h 00min", progress: 0,
    items: [
      { fcode: "F0900", title: "Introdução ao GitHub Actions", dur: "12:00", done: false },
      { fcode: "F0901", title: "Workflows e triggers", dur: "15:30", done: false },
      { fcode: "F0902", title: "Jobs e steps", dur: "11:45", done: false },
      { fcode: "F0903", title: "Secrets e environments", dur: "14:20", done: false },
    ],
  },
]

export const CURRENT_LESSON_FCODE = "F0003"

export const LESSON_META = [
  { icon: Clock,        label: "Duração",  value: "16:30" },
  { icon: BookOpen,     label: "Módulo",   value: "1 de 5" },
  { icon: CheckCircle2, label: "Status",   value: "Assistindo" },
  { icon: Download,     label: "Offline",  value: "Disponível" },
]
