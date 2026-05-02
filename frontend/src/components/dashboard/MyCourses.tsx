import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress, ProgressValue } from "@/components/ui/progress"
import { dashboardService } from "@/services/dashboard"
import { useFetch } from "@/hooks/useFetch"

export function MyCourses() {
  const { data, loading } = useFetch(() => dashboardService.myCourses(), [])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Meus Cursos</CardTitle>
        <CardAction>
          <Link to="/courses">
            <Button variant="ghost" size="sm">Ver todos</Button>
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        ) : (data ?? []).length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            Nenhum curso ainda. Adicione uma integração Telegram para começar.
          </p>
        ) : (
          <div className="space-y-3">
            {(data ?? []).map((c) => (
              <Link key={c.id} to={`/course/${c.id}`}>
                <div className="border border-border hover:border-primary/30 transition-colors overflow-hidden">
                  <div className="p-3">
                    <div className="flex justify-between items-center mb-1.5">
                      <p className="text-xs font-semibold">{c.title}</p>
                      <span className="text-[11px] text-muted-foreground">{c.hours}h</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground mb-2">
                      {c.lessons} aulas · {c.modules} módulos
                    </p>
                    <Progress value={c.progress_pct}>
                      <ProgressValue />
                    </Progress>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
