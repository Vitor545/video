import { useEffect, useState, useMemo } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, LabelList } from "recharts"
import { DOWNLOAD_CHART_CONFIG } from "@/constants/downloads"
import { coursesService } from "@/services/courses"
import type { Course, Video } from "@/services/courses"
import { Loader2 } from "lucide-react"

export function ModuleDownloadChart() {
  const [courses, setCourses] = useState<Course[]>([])
  const [selectedCourseId, setSelectedCourseId] = useState<string>("")
  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(false)

  // Fetch courses on mount
  useEffect(() => {
    coursesService.list().then(data => {
      setCourses(data)
      if (data.length > 0) {
        setSelectedCourseId(data[0].id.toString())
      }
    }).catch(console.error)
  }, [])

  // Fetch videos when course changes
  useEffect(() => {
    if (selectedCourseId) {
      setLoading(true)
      coursesService.listVideos(parseInt(selectedCourseId))
        .then(data => setVideos(data))
        .catch(console.error)
        .finally(() => setLoading(false))
    }
  }, [selectedCourseId])

  const chartData = useMemo(() => {
    if (videos.length === 0) return []

    const modules: Record<string, { total: number, done: number }> = {}

    videos.forEach(v => {
      const mod = v.module_name || "Módulo"
      if (!modules[mod]) {
        modules[mod] = { total: 0, done: 0 }
      }
      modules[mod].total += 1
      if (v.download_status === "done") {
        modules[mod].done += 1
      }
    })

    return Object.entries(modules)
      .map(([name, stats]) => ({
        module: name.length > 20 ? name.substring(0, 20) + "..." : name,
        fullModule: name,
        total: stats.total,
        done: stats.done
      }))
      .sort((a, b) => b.total - a.total) // Sort by most videos
      .slice(0, 10) // Show top 10 modules max for chart readability
  }, [videos])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Downloads por Módulo</CardTitle>
        <CardDescription>Acompanhamento detalhado do curso</CardDescription>
        <CardAction>
          <Select value={selectedCourseId} onValueChange={(val) => setSelectedCourseId(val || "")}>
            <SelectTrigger size="sm" className="w-[180px]">
              <SelectValue placeholder="Selecione..." />
            </SelectTrigger>
            <SelectContent>
              {courses.map(c => (
                <SelectItem key={c.id} value={c.id.toString()}>{c.title}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardAction>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-[160px] w-full flex items-center justify-center">
            <Loader2 className="animate-spin text-muted-foreground" />
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-[160px] w-full flex items-center justify-center text-sm text-muted-foreground border border-dashed border-border">
            Nenhum dado disponível
          </div>
        ) : (
          <ChartContainer config={DOWNLOAD_CHART_CONFIG} className="h-[160px] w-full">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 0, right: 30, left: 0, bottom: 0 }}
              barSize={8}
              barGap={2}
            >
              <CartesianGrid horizontal={false} stroke="rgba(255,255,255,0.04)" />
              <YAxis
                dataKey="module"
                type="category"
                tick={{ fontSize: 10, fill: "#6b7280" }}
                axisLine={false}
                tickLine={false}
                width={80}
              />
              <XAxis type="number" hide />
              <ChartTooltip
                content={<ChartTooltipContent />}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="total" fill="var(--color-total)" radius={[0, 3, 3, 0]} name="Total" />
              <Bar dataKey="done" fill="var(--color-done)" radius={[0, 3, 3, 0]} name="Baixados">
                <LabelList
                  dataKey="done"
                  position="right"
                  style={{ fontSize: 9, fill: "#6b7280" }}
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
