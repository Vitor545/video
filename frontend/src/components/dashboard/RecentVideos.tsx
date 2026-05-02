import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { dashboardService } from "@/services/dashboard"
import { useFetch } from "@/hooks/useFetch"

function fmtDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "—"
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, "0")}`
}

export function RecentVideos() {
  const { data, loading } = useFetch(() => dashboardService.recent(8), [])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Continuar Assistindo</CardTitle>
        <CardDescription>Onde você parou</CardDescription>
        <CardAction>
          <Link to="/courses">
            <Button variant="ghost" size="sm">Ver todos</Button>
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : (data ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            Nenhuma aula assistida ainda. Comece um curso para ver seu progresso aqui.
          </p>
        ) : (
          <div className="space-y-1">
            {(data ?? []).map((v) => (
              <Link
                key={v.video_id}
                to={`/course/${v.course_id}?video=${v.video_id}`}
                className="flex items-center gap-3 p-2.5 hover:bg-accent cursor-pointer transition-colors"
              >
                <div
                  className="w-20 bg-muted flex items-center justify-center shrink-0 relative overflow-hidden"
                  style={{ height: 52 }}
                >
                  <span className="text-[10px] text-muted-foreground/50">Vídeo</span>
                  <span className="absolute bottom-1 right-1 bg-black/70 text-white text-[10px] px-1">
                    {fmtDuration(v.duration_seconds)}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{v.title}</p>
                  <p className="text-[11px] text-muted-foreground">
                    {v.module_name} · {v.fcode}
                  </p>
                  <Progress value={v.progress_pct} className="mt-1.5" />
                </div>
                <span className="text-xs text-muted-foreground shrink-0">{v.progress_pct}%</span>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
