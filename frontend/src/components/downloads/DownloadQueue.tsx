import { useCallback, useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Loader2, RefreshCw, X } from "lucide-react"
import { STATUS_ICON, STATUS_BADGE } from "@/constants/downloads"
import { downloadsService } from "@/services/downloads"
import type { DownloadJob, StatusResponse } from "@/services/downloads"
import { useToast } from "@/hooks/use-toast"

const IN_FLIGHT: DownloadJob["status"][] = ["downloading", "pending", "retry_pending"]

function fmtDuration(seconds: number | null): string {
  if (!seconds || seconds <= 0) return ""
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, "0")}`
}

export function DownloadQueue({ refreshToken }: { refreshToken?: number }) {
  const [data, setData] = useState<StatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  const fetchStatus = useCallback(async () => {
    try {
      const res = await downloadsService.status()
      setData(res)
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  useEffect(() => {
    if (refreshToken === undefined) return
    fetchStatus()
  }, [refreshToken, fetchStatus])

  const handleRetry = async (jobId: number) => {
    try {
      await downloadsService.retryJob(jobId)
      toast({ title: "Retentativa iniciada" })
      fetchStatus()
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Erro desconhecido"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    }
  }

  if (loading && !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Em andamento</CardTitle>
          <CardDescription>Carregando fila…</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  const allJobs = data?.jobs ?? []
  const inFlightJobs = allJobs.filter((j) => IN_FLIGHT.includes(j.status))
  const failedJobs = allJobs.filter((j) => j.status === "failed")
  const activeCount = Object.keys(data?.worker.active ?? {}).length

  const renderJob = (job: DownloadJob) => {
    const isDownloading = job.status === "downloading"
    const activeData = data?.worker.active[job.id]
    let progress = 0
    if (isDownloading && activeData && activeData.total_bytes > 0) {
      progress = (activeData.progress_bytes / activeData.total_bytes) * 100
    }
    const statusKey = job.status === "retry_pending" ? "failed" : (job.status as keyof typeof STATUS_ICON)

    const subtitle = [
      job.course_title ?? "Curso desconhecido",
      job.module_name,
    ]
      .filter(Boolean)
      .join(" · ")

    return (
      <div
        key={job.id}
        className="group relative flex items-center gap-4 p-4 bg-background border border-border hover:border-primary/20 transition-colors"
      >
        <div className="w-9 h-9 bg-muted flex items-center justify-center shrink-0">
          {STATUS_ICON[statusKey]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-sm font-semibold truncate">
              {job.video_title ?? `Vídeo #${job.video_id}`}
            </span>
            {job.fcode && (
              <span className="text-[10px] font-mono text-muted-foreground shrink-0 px-1.5 py-0.5 bg-muted">
                {job.fcode}
              </span>
            )}
            {job.duration_seconds ? (
              <span className="text-[10px] text-muted-foreground/70 shrink-0">
                {fmtDuration(job.duration_seconds)}
              </span>
            ) : null}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground truncate">{subtitle}</span>
            {isDownloading && (
              <div className="flex-1 h-1.5 bg-muted overflow-hidden ml-2 max-w-[200px]">
                <div className="h-full bg-yellow-400" style={{ width: `${progress}%` }} />
              </div>
            )}
            {isDownloading && (
              <span className="text-[10px] text-muted-foreground shrink-0 font-mono">
                {Math.round(progress)}%
              </span>
            )}
          </div>
          {job.error && (
            <div className="text-[10px] text-destructive mt-1 truncate max-w-md">
              {job.error}
              {job.attempts > 0 && ` · ${job.attempts} tentativa(s)`}
            </div>
          )}
        </div>
        <div className="shrink-0 flex items-center justify-end gap-3 min-w-[120px]">
          <div className="transition-opacity group-hover:opacity-0 absolute right-4">
            {STATUS_BADGE[statusKey]}
          </div>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity absolute right-4 bg-background pl-2">
            {(job.status === "failed" || job.status === "retry_pending") && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                onClick={() => handleRetry(job.id)}
              >
                <RefreshCw size={14} />
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-destructive"
            >
              <X size={14} />
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Em andamento</CardTitle>
          <CardDescription>
            {inFlightJobs.length} {inFlightJobs.length === 1 ? "item" : "itens"} na fila
            {activeCount > 0 && ` · ${activeCount} baixando agora`}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {inFlightJobs.length === 0 ? (
            <div className="text-center py-6 text-sm text-muted-foreground border border-dashed border-border">
              Nenhum download em andamento.
            </div>
          ) : (
            inFlightJobs.map(renderJob)
          )}
        </CardContent>
      </Card>

      {failedJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-destructive">Falhas</CardTitle>
            <CardDescription>
              {failedJobs.length} {failedJobs.length === 1 ? "download falhou" : "downloads falharam"} —
              clique no botão de retry para tentar novamente.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">{failedJobs.map(renderJob)}</CardContent>
        </Card>
      )}
    </div>
  )
}
