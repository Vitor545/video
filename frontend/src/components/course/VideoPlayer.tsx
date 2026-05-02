import { useEffect, useRef, useState } from "react"
import { Loader2, PlayCircle, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { videosService } from "@/services/videos"

interface VideoPlayerProps {
  videoId: number
  /** Posição inicial em segundos (vinda do backend, /videos/{id}/progress). */
  initialProgress?: number
  /** Título da próxima aula. Quando presente, mostra overlay de auto-advance ao final. */
  nextLessonTitle?: string | null
  /** Callback chamado quando o vídeo é dado como concluído (>=95%). */
  onCompleted?: () => void
  /**
   * Callback disparado para avançar para a próxima aula.
   * Acionado automaticamente após o countdown de auto-advance.
   */
  onAdvance?: () => void
}

const SAVE_INTERVAL_MS = 10_000
const AUTO_ADVANCE_SECONDS = 5
// Renova a URL presigned 5min antes de expirar para não interromper o playback
const REFRESH_BUFFER_MS = 5 * 60 * 1000

export function VideoPlayer({
  videoId,
  initialProgress = 0,
  nextLessonTitle,
  onCompleted,
  onAdvance,
}: VideoPlayerProps) {
  const ref = useRef<HTMLVideoElement>(null)
  const lastSavedRef = useRef<number>(initialProgress)
  const completedRef = useRef<boolean>(false)
  const advanceTriggeredRef = useRef<boolean>(false)
  const onCompletedRef = useRef<VideoPlayerProps["onCompleted"]>(onCompleted)
  const onAdvanceRef = useRef<VideoPlayerProps["onAdvance"]>(onAdvance)
  const [streamUrl, setStreamUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [autoAdvanceLeft, setAutoAdvanceLeft] = useState<number | null>(null)

  useEffect(() => {
    onCompletedRef.current = onCompleted
  }, [onCompleted])

  useEffect(() => {
    onAdvanceRef.current = onAdvance
  }, [onAdvance])

  // Reset ao trocar de vídeo
  useEffect(() => {
    lastSavedRef.current = 0
    completedRef.current = false
    advanceTriggeredRef.current = false
    setError(null)
    setStreamUrl(null)
    setAutoAdvanceLeft(null)
  }, [videoId])

  useEffect(() => {
    lastSavedRef.current = Math.max(lastSavedRef.current, initialProgress)
  }, [initialProgress])

  // Busca URL presigned e renova periodicamente
  useEffect(() => {
    let cancelled = false
    let refreshTimer: ReturnType<typeof setTimeout> | null = null

    const load = async () => {
      try {
        const { url, expires_in } = await videosService.getStreamUrl(videoId)
        if (cancelled) return
        setStreamUrl(url)
        const refreshIn = Math.max(60_000, expires_in * 1000 - REFRESH_BUFFER_MS)
        refreshTimer = setTimeout(load, refreshIn)
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Erro ao carregar vídeo")
        }
      }
    }
    void load()

    return () => {
      cancelled = true
      if (refreshTimer) clearTimeout(refreshTimer)
    }
  }, [videoId])

  // Aplica posição inicial ao carregar metadata
  useEffect(() => {
    const v = ref.current
    if (!v || !streamUrl) return
    const onLoaded = () => {
      if (initialProgress > 0 && initialProgress < (v.duration || Infinity) - 5) {
        v.currentTime = initialProgress
      }
    }
    v.addEventListener("loadedmetadata", onLoaded)
    return () => v.removeEventListener("loadedmetadata", onLoaded)
  }, [streamUrl, initialProgress])

  // Auto-save a cada 10s
  useEffect(() => {
    const v = ref.current
    if (!v || !streamUrl) return

    const save = async (force = false) => {
      const current = Math.floor(v.currentTime)
      const duration = v.duration || 0
      const completed = duration > 0 && current >= duration * 0.95
      if (!force && Math.abs(current - lastSavedRef.current) < 3) return
      try {
        await videosService.saveProgress(videoId, current, completed)
        lastSavedRef.current = current
        if (completed && !completedRef.current) {
          completedRef.current = true
          onCompletedRef.current?.()
        }
      } catch {
        // ignora — tenta de novo no próximo intervalo
      }
    }

    const interval = setInterval(() => {
      if (!v.paused) save()
    }, SAVE_INTERVAL_MS)

    const triggerAdvance = () => {
      if (advanceTriggeredRef.current) return
      advanceTriggeredRef.current = true
      if (!completedRef.current) {
        completedRef.current = true
        onCompletedRef.current?.()
      }
      void save(true)
      if (onAdvanceRef.current) {
        setAutoAdvanceLeft(AUTO_ADVANCE_SECONDS)
      }
    }

    const maybeTriggerAdvance = () => {
      const dur = v.duration
      if (!dur || !isFinite(dur)) return false
      if (v.ended || v.currentTime >= dur - 0.25) {
        triggerAdvance()
        return true
      }
      return false
    }

    const onPause = () => {
      void save(true)
      maybeTriggerAdvance()
    }
    const onEndedHandler = () => triggerAdvance()
    const onTimeUpdate = () => {
      maybeTriggerAdvance()
    }
    const onSeeked = () => {
      maybeTriggerAdvance()
    }

    v.addEventListener("pause", onPause)
    v.addEventListener("ended", onEndedHandler)
    v.addEventListener("timeupdate", onTimeUpdate)
    v.addEventListener("seeked", onSeeked)

    const endWatchdog = setInterval(() => {
      if (!advanceTriggeredRef.current) maybeTriggerAdvance()
    }, 500)

    return () => {
      clearInterval(interval)
      clearInterval(endWatchdog)
      v.removeEventListener("pause", onPause)
      v.removeEventListener("ended", onEndedHandler)
      v.removeEventListener("timeupdate", onTimeUpdate)
      v.removeEventListener("seeked", onSeeked)
      void save(true)
    }
  }, [videoId, nextLessonTitle, streamUrl])

  // Countdown do auto-advance
  useEffect(() => {
    if (autoAdvanceLeft === null) return
    if (autoAdvanceLeft <= 0) {
      setAutoAdvanceLeft(null)
      onAdvanceRef.current?.()
      return
    }
    const t = setTimeout(() => setAutoAdvanceLeft((n) => (n === null ? null : n - 1)), 1000)
    return () => clearTimeout(t)
  }, [autoAdvanceLeft])

  return (
    <div className="aspect-video bg-black relative overflow-hidden border border-border">
      {streamUrl ? (
        <video
          ref={ref}
          key={streamUrl}
          src={streamUrl}
          controls
          autoPlay
          preload="auto"
          className="w-full h-full"
          onError={() => setError("Não foi possível carregar o vídeo. Verifique se o download terminou.")}
        />
      ) : !error ? (
        <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
          <Loader2 className="animate-spin" />
        </div>
      ) : null}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/80 text-sm text-muted-foreground p-4 text-center">
          {error}
        </div>
      )}

      {autoAdvanceLeft !== null && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/85 backdrop-blur-sm">
          <div className="bg-background border border-border p-6 max-w-md w-[90%] text-center space-y-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">Próxima aula em {autoAdvanceLeft}s</p>
            <p className="text-base font-semibold leading-snug">{nextLessonTitle || "Próxima aula"}</p>
            <div className="h-1 bg-muted overflow-hidden">
              <div
                className="h-full bg-primary transition-[width] duration-1000 ease-linear"
                style={{ width: `${((AUTO_ADVANCE_SECONDS - autoAdvanceLeft) / AUTO_ADVANCE_SECONDS) * 100}%` }}
              />
            </div>
            <div className="flex gap-2 justify-center">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setAutoAdvanceLeft(null)}
              >
                <X size={14} className="mr-1" /> Cancelar
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  setAutoAdvanceLeft(null)
                  onAdvanceRef.current?.()
                }}
              >
                <PlayCircle size={14} className="mr-1" /> Tocar agora
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
