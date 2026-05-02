import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { RadialBarChart, RadialBar, PolarGrid, PolarAngleAxis } from "recharts"
import { RADIAL_CONFIG } from "@/constants/dashboard"
import { dashboardService } from "@/services/dashboard"
import { useFetch } from "@/hooks/useFetch"

const PALETTE = ["#1e3a5f", "#1d4ed8", "#2563eb", "#60a5fa", "#93c5fd"]

export function ModuleRadialChart({ courseId }: { courseId: number | null }) {
  const { data, loading } = useFetch(() => dashboardService.modules(5, courseId), [courseId])
  const chartData = (data ?? []).map((d, i) => ({
    name: d.module_name,
    value: d.percent,
    fill: PALETTE[i % PALETTE.length],
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Progresso por Módulo</CardTitle>
        <CardDescription>Módulos próximos do que você está assistindo</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-[180px] w-full" />
        ) : chartData.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-12">
            Sem progresso por módulo ainda.
          </p>
        ) : (
          <>
            <ChartContainer config={RADIAL_CONFIG} className="h-[180px] w-full">
              <RadialBarChart
                cx="50%" cy="50%"
                innerRadius="20%"
                outerRadius="90%"
                data={chartData}
                startAngle={90}
                endAngle={-270}
              >
                <PolarGrid gridType="circle" radialLines={false} stroke="rgba(255,255,255,0.05)" />
                <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                <RadialBar dataKey="value" background={{ fill: "#1a1a1a" }} cornerRadius={4} />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      formatter={(v, _, __, ___, data) => {
                        const item = data as { name?: string } | undefined
                        const name = typeof item?.name === "string" ? item.name : ""
                        const value = typeof v === "number" ? `${v}%` : `${String(v)}%`
                        return (
                          <div className="flex w-full min-w-56 items-center gap-3">
                            <span className="text-muted-foreground truncate">{name}</span>
                            <span className="ml-auto font-mono font-medium text-foreground tabular-nums whitespace-nowrap">
                              {value}
                            </span>
                          </div>
                        )
                      }}
                    />
                  }
                  cursor={false}
                />
              </RadialBarChart>
            </ChartContainer>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1">
              {chartData.map(d => (
                <div key={d.name} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: d.fill }} />
                  <span className="truncate">{d.name}</span>
                  <span className="ml-auto font-mono text-foreground">{d.value}%</span>
                </div>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
