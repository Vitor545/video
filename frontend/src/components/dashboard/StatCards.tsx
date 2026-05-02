import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { TrendingUp, Loader2 } from "lucide-react"
import { dashboardService } from "@/services/dashboard"
import { useCallback, useEffect, useState } from "react"
import type { DashboardStats } from "@/services/dashboard"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

type CourseOption = { id: number; title: string }

export function StatCards({
  courses,
  courseValue,
  onCourseValueChange,
  courseId,
}: {
  courses: CourseOption[]
  courseValue: string
  onCourseValueChange: (value: string) => void
  courseId: number | null
}) {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  const studyTime = (() => {
    if (!stats) return { value: "—", unit: "" }
    const hours = typeof stats.hours_this_month === "number" ? stats.hours_this_month : 0
    const minutes = Math.round(hours * 60)
    if (minutes < 60) {
      return { value: String(minutes), unit: "min este mês" }
    }
    const v = hours.toLocaleString("pt-BR", {
      maximumFractionDigits: hours < 10 ? 1 : 0,
    })
    return { value: v, unit: "h este mês" }
  })()

  const fetchStats = useCallback(async () => {
    try {
      const data = await dashboardService.stats(courseId)
      setStats(data)
    } finally {
      setLoading(false)
    }
  }, [courseId])

  useEffect(() => {
    setLoading(true)
    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [fetchStats])

  const items =
    courseId == null
      ? [
          {
            label: "Cursos Ativos",
            value: stats ? stats.active_courses : "—",
            unit: "cursos",
          },
          {
            label: "Aulas Concluídas",
            value: stats ? stats.lessons_completed : "—",
            unit: stats ? `de ${stats.total_lessons}` : "",
          },
          {
            label: "Tempo Estudado",
            value: studyTime.value,
            unit: studyTime.unit,
          },
          {
            label: "Em Download",
            value: stats ? stats.queued_downloads : "—",
            unit: "na fila",
          },
        ]
      : [
          {
            label: "Progresso",
            value: stats ? stats.progress_pct ?? 0 : "—",
            unit: "%",
          },
          {
            label: "Aulas Concluídas",
            value: stats ? stats.lessons_completed : "—",
            unit: stats ? `de ${stats.total_lessons}` : "",
          },
          {
            label: "Tempo Estudado",
            value: studyTime.value,
            unit: studyTime.unit,
          },
          {
            label: "Em Download",
            value: stats ? stats.queued_downloads : "—",
            unit: "na fila",
          },
        ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
      {items.map(({ label, value, unit }, idx) => (
        <Card key={label}>
          <CardContent>
            {idx === 0 ? (
              <div className="flex flex-col gap-2 mb-4 sm:flex-row sm:items-center sm:justify-between">
                <span className="text-xs text-muted-foreground font-medium">{label}</span>
                <div className="flex items-center gap-2">
                  {loading && <Loader2 size={12} className="animate-spin text-muted-foreground" />}
                  <Select value={courseValue} onValueChange={onCourseValueChange}>
                    <SelectTrigger size="sm" className="w-full min-w-32 sm:w-44">
                      <SelectValue>
                        {courseId == null
                          ? "Todos"
                          : courses.find((c) => c.id === courseId)?.title ?? "Curso"}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent align="end">
                      <SelectItem value="all">Todos</SelectItem>
                      {courses.map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>
                          {c.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs text-muted-foreground font-medium">{label}</span>
                {loading && <Loader2 size={12} className="animate-spin text-muted-foreground" />}
              </div>
            )}
            <div className="text-2xl font-bold leading-none mb-1">
              {loading ? (
                <Skeleton className="h-7 w-16" />
              ) : (
                <>
                  {value}{" "}
                  <span className="text-xs font-normal text-muted-foreground">{unit}</span>
                </>
              )}
            </div>
            <div className="flex items-center gap-1 text-xs text-green-400 mt-2">
              <TrendingUp size={11} /> em tempo real
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
