import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { LineChart, Line, XAxis, YAxis, CartesianGrid } from "recharts"
import { STREAK_CONFIG } from "@/constants/dashboard"
import { dashboardService } from "@/services/dashboard"
import { useFetch } from "@/hooks/useFetch"

export function StreakChart({ courseId }: { courseId: number | null }) {
  const { data, loading } = useFetch(() => dashboardService.streak(courseId), [courseId])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Streak de Estudos</CardTitle>
        <CardDescription>Minutos estudados por dia (semana atual)</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-[150px] w-full" />
        ) : (
          <ChartContainer config={STREAK_CONFIG} className="h-[150px] w-full">
            <LineChart data={data ?? []} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
              <YAxis hide />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    hideLabel
                    formatter={(v, _, __, ___, data) => {
                      const day = typeof data?.day === "string" ? data.day : ""
                      const minutes = typeof v === "number" ? v : Number(v)
                      const value = Number.isFinite(minutes) ? `${minutes} min` : `${String(v)} min`
                      return (
                        <div className="flex min-w-40 items-center gap-3">
                          <span className="text-muted-foreground">{day}</span>
                          <span className="ml-auto font-mono font-medium text-foreground tabular-nums whitespace-nowrap">
                            {value}
                          </span>
                        </div>
                      )
                    }}
                  />
                }
                cursor={{ stroke: "rgba(255,255,255,0.1)", strokeWidth: 1 }}
              />
              <Line
                type="monotone"
                dataKey="min"
                stroke="var(--color-min)"
                strokeWidth={2}
                dot={{ r: 2, fill: "var(--color-min)", strokeWidth: 0 }}
                activeDot={{ r: 4, fill: "var(--color-min)", strokeWidth: 0 }}
              />
            </LineChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
