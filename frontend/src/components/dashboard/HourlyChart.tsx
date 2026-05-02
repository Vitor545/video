import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, LabelList } from "recharts"
import { HOURLY_CONFIG } from "@/constants/dashboard"
import { dashboardService } from "@/services/dashboard"
import { useFetch } from "@/hooks/useFetch"

export function HourlyChart({ courseId }: { courseId: number | null }) {
  const { data, loading } = useFetch(() => dashboardService.hourly(courseId), [courseId])
  // Mostra só horas com atividade (ou 6h–22h se tudo zero) para não poluir
  const filtered = (data ?? []).filter((d, i) => d.min > 0 || (i >= 6 && i <= 22))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Horário de Estudo</CardTitle>
        <CardDescription>Minutos estudados por hora do dia</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-[150px] w-full" />
        ) : (
          <ChartContainer config={HOURLY_CONFIG} className="h-[150px] w-full">
            <BarChart data={filtered} barSize={20} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "#6b7280" }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    hideLabel
                    formatter={(v, _, __, ___, data) => {
                      const item = data as { hour?: string } | undefined
                      const hour = typeof item?.hour === "string" ? item.hour : ""
                      const minutes = typeof v === "number" ? v : Number(v)
                      const value = Number.isFinite(minutes) ? `${minutes} min` : `${String(v)} min`
                      return (
                        <div className="flex min-w-40 items-center gap-3">
                          <span className="text-muted-foreground">{hour}</span>
                          <span className="ml-auto font-mono font-medium text-foreground tabular-nums whitespace-nowrap">
                            {value}
                          </span>
                        </div>
                      )
                    }}
                  />
                }
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="min" fill="var(--color-min)" radius={[3, 3, 0, 0]}>
                <LabelList
                  dataKey="min"
                  position="top"
                  style={{ fontSize: 9, fill: "#4b5563" }}
                  formatter={(v) => (Number(v) > 0 ? v : "")}
                />
              </Bar>
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
