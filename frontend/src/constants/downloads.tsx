import { CheckCircle2, XCircle, Clock, Loader2, Send } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { ChartConfig } from "@/components/ui/chart"

export const DOWNLOAD_QUEUE = [
  { fcode: "F0218", title: "Services no Kubernetes", course: "DevOps Pro 2", module: "Kubernetes 2.0", source: "Telegram", status: "downloading", progress: 64 },
  { fcode: "F0219", title: "ConfigMaps e Secrets", course: "DevOps Pro 2", module: "Kubernetes 2.0", status: "pending", progress: 0 },
  { fcode: "F0220", title: "Ingress Controller", course: "SRE Foundations", module: "Observability", status: "pending", progress: 0 },
]

export const DOWNLOADED_STORAGE = [
  {
    id: "devops-pro",
    course: "DevOps Pro 2",
    totalSize: "14.2 GB",
    lessonsCount: 1113,
    files: [
      { fcode: "F0101", title: "Introdução ao Git", module: "Git e GitHub", size: "245 MB", date: "Hoje" },
      { fcode: "F0102", title: "Branches e merges", module: "Git e GitHub", size: "312 MB", date: "Ontem" },
      { fcode: "F0039", title: "Introdução aos Containers", module: "Docker 2.0", size: "450 MB", date: "10 Abr" },
      { fcode: "F0200", title: "Introdução ao Kubernetes", module: "Kubernetes 2.0", size: "180 MB", date: "12 Abr" },
    ]
  },
  {
    id: "sre",
    course: "SRE Foundations",
    totalSize: "4.8 GB",
    lessonsCount: 340,
    files: [
      { fcode: "F0300", title: "Métricas com Prometheus", module: "Observability", size: "510 MB", date: "15 Abr" },
    ]
  }
]

export const MODULE_HISTORY_BY_COURSE: Record<string, { module: string; done: number; total: number }[]> = {
  "DevOps Pro 2": [
    { module: "Linux", done: 93, total: 93 },
    { module: "Git", done: 20, total: 20 },
    { module: "Docker", done: 119, total: 176 },
    { module: "K8s", done: 26, total: 216 },
    { module: "Actions", done: 0, total: 93 },
  ],
  "SRE Foundations": [
    { module: "Observability", done: 45, total: 120 },
    { module: "SLOs & Error Budgets", done: 0, total: 80 },
    { module: "Incident Response", done: 0, total: 140 },
  ]
}

export const MODAL_COURSES = [
  { id: "c1", title: "DevOps Pro 2", source: "Telegram" },
  { id: "c2", title: "SRE Foundations", source: "Telegram" }
]

export const MOCK_MODULES = [
  {
    id: "m1", title: "Linux Basics", lessons: [
      { id: "l1", title: "Introdução ao Linux", duration: "10:00" },
      { id: "l2", title: "Permissões e Usuários", duration: "15:20" },
      { id: "l3", title: "Gerenciamento de Pacotes", duration: "20:05" },
    ]
  },
  {
    id: "m2", title: "Aulas Avulsas (Módulo Genérico)", lessons: [
      { id: "l4", title: "Como criar uma VM na Nuvem", duration: "08:45" },
      { id: "l5", title: "Configuração de IP Fixo", duration: "12:10" },
    ]
  }
]

export const STATUS_ICON: Record<string, React.ReactNode> = {
  downloading: <Loader2 size={14} className="text-yellow-400 animate-spin" />,
  pending: <Clock size={14} className="text-muted-foreground" />,
  done: <CheckCircle2 size={14} className="text-green-400" />,
  failed: <XCircle size={14} className="text-red-400" />,
}

export const STATUS_BADGE: Record<string, React.ReactNode> = {
  downloading: <Badge variant="outline" className="text-yellow-400 border-yellow-400/30 text-[10px] h-4 py-0">Baixando</Badge>,
  pending: <Badge variant="outline" className="text-[10px] h-4 py-0">Aguardando</Badge>,
  done: <Badge variant="outline" className="text-green-400 border-green-400/30 text-[10px] h-4 py-0">Concluído</Badge>,
  failed: <Badge variant="destructive" className="text-[10px] h-4 py-0">Erro</Badge>,
}

export const SOURCE_ICON_SMALL: Record<string, React.ReactNode> = {
  "Telegram": <Send size={10} className="text-[#0088cc]" />,
}

export const DOWNLOAD_CHART_CONFIG = {
  total: { label: "Total", color: "#2a2a2a" },
  done: { label: "Baixados", color: "#3b82f6" },
} satisfies ChartConfig
