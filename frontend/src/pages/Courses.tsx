import AppLayout from "@/components/layout/AppLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { Link } from "react-router-dom"
import { BookOpen } from "lucide-react"
import { dashboardService } from "@/services/dashboard"
import { useFetch } from "@/hooks/useFetch"

export default function Courses() {
  const { data, loading, error } = useFetch(() => dashboardService.myCourses(), [])
  const courses = data ?? []

  return (
    <AppLayout title="Cursos" subtitle="Gerencie seus estudos">
      <div>
        <h2 className="text-lg font-bold mb-4">Meus Cursos</h2>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-40 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="bg-destructive/10 text-destructive p-4 border border-destructive/30">
            {error}
          </div>
        ) : courses.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-border">
            <BookOpen size={36} className="mx-auto text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground mb-1">Você ainda não tem cursos.</p>
            <p className="text-xs text-muted-foreground">
              Adicione uma{" "}
              <Link to="/management" className="text-primary hover:underline">
                integração Telegram
              </Link>{" "}
              para sincronizar seu primeiro curso.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {courses.map((c) => (
              <Link key={c.id} to={`/course/${c.id}`}>
                <Card className="hover:border-primary/50 transition-colors cursor-pointer group">
                  <CardHeader className="pb-4">
                    <div className="flex items-center justify-between mb-1">
                      <CardTitle className="text-sm group-hover:text-primary transition-colors truncate">
                        {c.title}
                      </CardTitle>
                      <BookOpen size={16} className="text-muted-foreground shrink-0 ml-2" />
                    </div>
                    <CardDescription className="line-clamp-2">
                      {c.completed > 0
                        ? `${c.completed} de ${c.lessons} aulas concluídas`
                        : "Comece agora — selecione uma aula para assistir."}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="flex justify-between items-center mb-1.5 text-[11px] text-muted-foreground">
                      <span>
                        {c.lessons} aulas · {c.modules} módulos
                      </span>
                      <span>{c.hours}h</span>
                    </div>
                    <Progress value={c.progress_pct} className="h-1.5" />
                    <div className="mt-1.5 text-[10px] font-medium text-right text-muted-foreground">
                      {c.progress_pct}% concluído
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
