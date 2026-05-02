import { useCallback, useEffect, useMemo, useState } from "react"
import { useParams, useSearchParams } from "react-router-dom"
import AppLayout from "@/components/layout/AppLayout"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { CheckCircle2, Loader2, PlayCircle } from "lucide-react"
import { VideoPlayer } from "@/components/course/VideoPlayer"
import { LessonDetails } from "@/components/course/LessonDetails"
import { ModuleList } from "@/components/course/ModuleList"
import { coursesService, type CourseDetail, type Video } from "@/services/courses"
import { videosService } from "@/services/videos"
import { useToast } from "@/hooks/use-toast"

export default function Course() {
  const { id } = useParams<{ id: string }>()
  const courseId = Number(id)
  const [searchParams, setSearchParams] = useSearchParams()
  const initialVideoParam = searchParams.get("video")

  const [detail, setDetail] = useState<CourseDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [currentVideoId, setCurrentVideoId] = useState<number | null>(null)
  const [markingCompleted, setMarkingCompleted] = useState(false)
  const { toast } = useToast()

  // Carrega detalhe do curso APENAS quando courseId muda — trocar de aula
  // não recarrega o curso (evita sobrescrever o estado de "completed" local).
  useEffect(() => {
    let cancelled = false
    setError(null)
    coursesService
      .get(courseId)
      .then((d) => {
        if (cancelled) return
        setDetail(d)
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Erro ao carregar curso"),
      )
    return () => {
      cancelled = true
    }
  }, [courseId])

  // Enquanto houver vídeos pendentes/baixando, refaz o fetch do curso a cada
  // 5s para que aulas recém-baixadas apareçam sem precisar recarregar a página.
  // Pausa enquanto uma conclusão estiver em voo para não sobrescrever o
  // optimistic update de applyCompletion.
  const hasPendingDownloads = useMemo(
    () =>
      detail?.modules.some((m) =>
        m.videos.some((v) => v.download_status !== "done"),
      ) ?? false,
    [detail],
  )
  useEffect(() => {
    if (!hasPendingDownloads) return
    let cancelled = false
    const tick = async () => {
      if (markingCompleted) return
      try {
        const d = await coursesService.get(courseId)
        if (!cancelled) setDetail(d)
      } catch {
        // ignora — tenta de novo no próximo intervalo
      }
    }
    const interval = setInterval(tick, 5000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [courseId, hasPendingDownloads, markingCompleted])

  // Quando o detalhe carrega ou o ?video= muda, escolhe vídeo inicial
  useEffect(() => {
    if (!detail) return
    const allVideos = detail.modules.flatMap((m) => m.videos)
    const fromQuery = initialVideoParam ? Number(initialVideoParam) : null
    const target =
      (fromQuery && allVideos.find((v) => v.id === fromQuery)) ||
      allVideos.find((v) => v.download_status === "done") ||
      null
    setCurrentVideoId((prev) => prev ?? target?.id ?? null)
  }, [detail, initialVideoParam])

  const allVideos = useMemo(
    () => detail?.modules.flatMap((m) => m.videos) ?? [],
    [detail],
  )
  const currentVideo = useMemo(
    () => allVideos.find((v) => v.id === currentVideoId) ?? null,
    [allVideos, currentVideoId],
  )
  const isCurrentFile = (currentVideo?.media_type ?? "video") !== "video"
  const currentModuleIndex = useMemo(() => {
    if (!detail || !currentVideo) return 0
    return detail.modules.findIndex((m) =>
      m.videos.some((v) => v.id === currentVideo.id),
    ) + 1
  }, [detail, currentVideo])

  const orderedVideos = useMemo(
    () => [...allVideos].sort((a, b) => a.order_index - b.order_index),
    [allVideos],
  )
  const currentOrderedIndex = currentVideo
    ? orderedVideos.findIndex((v) => v.id === currentVideo.id)
    : -1
  const nextVideo = currentOrderedIndex >= 0 ? orderedVideos[currentOrderedIndex + 1] : null

  /** Aplica completed=true localmente para um vídeo (idempotente). */
  const applyCompletion = useCallback((videoId: number) => {
    setDetail((prev) => {
      if (!prev) return prev
      const wasCompleted = prev.modules
        .flatMap((m) => m.videos)
        .find((v) => v.id === videoId)?.completed
      if (wasCompleted) return prev
      return {
        ...prev,
        completed: prev.completed + 1,
        progress_pct: prev.total_videos
          ? Math.round(((prev.completed + 1) / prev.total_videos) * 100)
          : 0,
        modules: prev.modules.map((m) => {
          const hasVideo = m.videos.some((v) => v.id === videoId)
          return {
            ...m,
            completed: hasVideo ? m.completed + 1 : m.completed,
            videos: m.videos.map((v) =>
              v.id === videoId ? { ...v, completed: true } : v,
            ),
          }
        }),
      }
    })
  }, [])

  const completeVideo = useCallback(async (videoId: number, durationSeconds?: number | null) => {
    applyCompletion(videoId)
    setMarkingCompleted(true)
    const progressSeconds = durationSeconds && durationSeconds > 0 ? durationSeconds : 1
    let lastError: unknown = null
    const delays = [0, 300, 1000, 2000]
    for (const delayMs of delays) {
      if (delayMs) await new Promise((r) => setTimeout(r, delayMs))
      try {
        await videosService.saveProgress(videoId, progressSeconds, true)
        setMarkingCompleted(false)
        return
      } catch (e) {
        lastError = e
      }
    }
    setMarkingCompleted(false)
    const msg = lastError instanceof Error ? lastError.message : "Não foi possível salvar a conclusão"
    toast({ title: "Falha ao concluir aula", description: msg, variant: "destructive" })
  }, [applyCompletion, toast])

  const handleSelect = useCallback((video: Video) => {
    setCurrentVideoId(video.id)
    setSearchParams({ video: String(video.id) }, { replace: true })
  }, [setSearchParams])

  const handleNext = () => {
    if (nextVideo) handleSelect(nextVideo)
  }

  const handleAutoAdvance = useCallback(() => {
    if (!currentVideo) return
    if ((currentVideo.media_type ?? "video") !== "video") return
    const videoId = currentVideo.id
    const durationSeconds = currentVideo.duration_seconds
    void (async () => {
      await completeVideo(videoId, durationSeconds)
      if (nextVideo) handleSelect(nextVideo)
    })()
  }, [completeVideo, currentVideo, nextVideo, handleSelect])

  const handleDownloadCurrent = useCallback(async () => {
    if (!currentVideo) return
    try {
      const { url } = await videosService.getDownloadUrl(currentVideo.id)
      window.open(url, "_blank", "noopener,noreferrer")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao gerar link de download"
      toast({ title: "Falha no download", description: msg, variant: "destructive" })
    }
  }, [currentVideo, toast])

  const currentFileSize = useMemo(() => {
    if (!currentVideo?.file_size) return null
    const bytes = currentVideo.file_size
    const units = ["B", "KB", "MB", "GB", "TB"]
    let value = bytes
    let unitIndex = 0
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024
      unitIndex += 1
    }
    const digits = unitIndex === 0 ? 0 : value < 10 ? 1 : 0
    return `${value.toFixed(digits)} ${units[unitIndex]}`
  }, [currentVideo?.file_size])

  const handleMarkCompleted = async () => {
    if (!currentVideo || markingCompleted) return
    setMarkingCompleted(true)
    try {
      // Salva progresso completo no backend e atualiza UI local
      await videosService.saveProgress(
        currentVideo.id,
        currentVideo.duration_seconds || 1,
        true,
      )
      applyCompletion(currentVideo.id)
      toast({ title: "Aula concluída" })
      if (nextVideo) handleSelect(nextVideo)
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro desconhecido"
      toast({ title: "Erro ao concluir aula", description: msg, variant: "destructive" })
    } finally {
      setMarkingCompleted(false)
    }
  }

  if (error) {
    return (
      <AppLayout title="Curso" subtitle="Erro">
        <div className="bg-destructive/10 text-destructive p-4 border border-destructive/30">
          {error}
        </div>
      </AppLayout>
    )
  }

  if (!detail) {
    return (
      <AppLayout title="Carregando…" subtitle="Visualização de Aula">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
          <div className="space-y-6">
            <Skeleton className="aspect-video w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
          <Skeleton className="h-[600px] w-full" />
        </div>
      </AppLayout>
    )
  }

  const lessonsCompleted = detail.completed
  const totalLessons = detail.total_videos

  return (
    <AppLayout
      title={detail.course.title}
      subtitle="Visualização de Aula"
      actions={
        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <span>
            {lessonsCompleted} de {totalLessons} concluídas
          </span>
          {currentVideo && (
            <Button
              variant={currentVideo.completed ? "secondary" : "default"}
              size="sm"
              onClick={handleMarkCompleted}
              disabled={markingCompleted || currentVideo.completed}
            >
              {markingCompleted ? (
                <Loader2 size={14} className="mr-2 animate-spin" />
              ) : (
                <CheckCircle2 size={14} className="mr-2" />
              )}
              {currentVideo.completed ? "Aula concluída" : "Concluir aula"}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={handleNext} disabled={!nextVideo}>
            Próxima aula <PlayCircle size={14} className="ml-2" />
          </Button>
        </div>
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
        <div className="space-y-6">
          {currentVideo ? (
            isCurrentFile ? (
              <div className="aspect-video bg-muted/30 border border-border flex flex-col items-center justify-center gap-3 text-sm text-muted-foreground">
                <div className="text-center px-6">
                  <div className="font-medium text-foreground">Arquivo</div>
                  <div className="text-xs mt-1">
                    {currentVideo.original_filename ?? currentVideo.title}
                  </div>
                  {currentFileSize && <div className="text-xs mt-1">{currentFileSize}</div>}
                </div>
                <Button onClick={handleDownloadCurrent} variant="default" size="sm">
                  Baixar arquivo
                </Button>
              </div>
            ) : (
              <VideoPlayer
                videoId={currentVideo.id}
                initialProgress={currentVideo.progress_seconds}
                nextLessonTitle={nextVideo?.title ?? null}
                onCompleted={() => {
                  void completeVideo(currentVideo.id, currentVideo.duration_seconds)
                }}
                onAdvance={handleAutoAdvance}
              />
            )
          ) : (
            <div className="aspect-video bg-muted/30 border border-border flex items-center justify-center text-sm text-muted-foreground">
              Selecione uma aula disponível na lista para começar.
            </div>
          )}

          {currentVideo && (
            <LessonDetails
              video={currentVideo}
              moduleIndex={currentModuleIndex}
              totalModules={detail.modules.length}
              description={detail.course.description}
            />
          )}
        </div>

        <ModuleList
          modules={detail.modules}
          currentVideoId={currentVideoId}
          progressPct={detail.progress_pct}
          onSelect={handleSelect}
        />
      </div>
    </AppLayout>
  )
}
