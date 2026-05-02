import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, ReferenceLine } from "recharts"
import { WEEKLY_CONFIG } from "@/constants/dashboard"
import { dashboardService } from "@/services/dashboard"
import { useFetch } from "@/hooks/useFetch"

const GOAL_HOURS = 5

export function WeeklyChart({ courseId }: { courseId: number | null }) {
  const { data, loading } = useFetch(() => dashboardService.weekly(8, courseId), [courseId])
  const chartData = (data ?? []).map((d) => ({ week: d.label, hours: d.hours, goal: GOAL_HOURS }))
  const fmt = (hours: unknown) => {
    const h = typeof hours === "number" ? hours : Number(hours)
    if (!Number.isFinite(h) || h <= 0) return "0 min"
    const minutes = Math.round(h * 60)
    if (minutes < 60) return `${minutes} min`
    const v = h.toLocaleString("pt-BR", { maximumFractionDigits: h < 10 ? 1 : 0 })
    return `${v} h`
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tempo Estudado por Semana</CardTitle>
        <CardDescription>Últimas 8 semanas vs meta de {GOAL_HOURS}h</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-[180px] w-full" />
        ) : (
          <ChartContainer config={WEEKLY_CONFIG} className="h-[180px] w-full">
            <AreaChart data={chartData} margin={{ top: 8, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="fillHours" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="var(--color-hours)" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="var(--color-hours)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="week" tick={{ fontSize: 10, fill: "#6b7280" }} axisLine={false} tickLine={false} />
              <YAxis
                tick={{ fontSize: 10, fill: "#6b7280" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => fmt(v)}
              />
              <ReferenceLine y={GOAL_HOURS} stroke="var(--color-goal)" strokeDasharray="4 4" strokeWidth={1.5} />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    hideLabel
                    formatter={(v, _, __, ___, data) => {
                      const week = typeof data?.week === "string" ? data.week : ""
                      return (
                        <div className="flex min-w-40 items-center gap-3">
                          <span className="text-muted-foreground">{week}</span>
                          <span className="ml-auto font-mono font-medium text-foreground tabular-nums whitespace-nowrap">
                            {fmt(v)}
                          </span>
                        </div>
                      )
                    }}
                  />
                }
                cursor={{ stroke: "rgba(255,255,255,0.08)", strokeWidth: 1 }}
              />
              <Area
                type="monotone"
                dataKey="hours"
                stroke="var(--color-hours)"
                strokeWidth={2}
                fill="url(#fillHours)"
                dot={false}
                activeDot={{ r: 4, fill: "var(--color-hours)", strokeWidth: 0 }}
              />
            </AreaChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
