import { useEffect, useState, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { Search, Loader2 } from "lucide-react"
import { coursesService } from "@/services/courses"
import type { Course, Video } from "@/services/courses"
import { downloadsService } from "@/services/downloads"
import { useToast } from "@/hooks/use-toast"

type Props = {
  open: boolean
  onClose: () => void
  onEnqueued?: () => void
}

export function AddDownloadModal({ open, onClose, onEnqueued }: Props) {
  const [courses, setCourses] = useState<Course[]>([])
  const [selectedCourseId, setSelectedCourseId] = useState<string>("")
  const [videos, setVideos] = useState<Video[]>([])
  const [loadingCourses, setLoadingCourses] = useState(false)
  const [loadingVideos, setLoadingVideos] = useState(false)
  const [saving, setSaving] = useState(false)

  const [search, setSearch] = useState("")
  const [selectedVideoIds, setSelectedVideoIds] = useState<Set<number>>(new Set())

  const { toast } = useToast()

  useEffect(() => {
    if (open) {
      setLoadingCourses(true)
      coursesService.list()
        .then(data => {
          setCourses(data)
          if (data.length > 0 && !selectedCourseId) {
            setSelectedCourseId(data[0].id.toString())
          }
        })
        .catch(err => console.error(err))
        .finally(() => setLoadingCourses(false))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    if (open && selectedCourseId) {
      setLoadingVideos(true)
      setSelectedVideoIds(new Set())
      coursesService.listVideos(parseInt(selectedCourseId))
        .then(data => setVideos(data))
        .catch(err => console.error(err))
        .finally(() => setLoadingVideos(false))
    }
  }, [selectedCourseId, open])

  // Process and filter videos
  const modules = useMemo(() => {
    const term = search.toLowerCase()

    // Group by module
    const grouped: Record<string, Video[]> = {}
    videos.forEach(v => {
      // Filter out already downloaded or downloading videos if we only want to show available
      // For now, let's show them all but maybe disable if done
      if (!grouped[v.module_name]) {
        grouped[v.module_name] = []
      }

      const matchTitle = v.title.toLowerCase().includes(term)
      const matchModule = v.module_name.toLowerCase().includes(term)

      if (matchTitle || matchModule) {
        grouped[v.module_name].push(v)
      }
    })

    return Object.entries(grouped)
      .filter(([, vids]) => vids.length > 0)
      .map(([name, vids]) => ({
        id: name,
        title: name,
        lessons: vids.sort((a, b) => a.order_index - b.order_index)
      }))
  }, [videos, search])

  const selectedLabel = courses.find(c => c.id.toString() === selectedCourseId)?.title

  const toggleVideo = (id: number) => {
    const next = new Set(selectedVideoIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setSelectedVideoIds(next)
  }

  const toggleModule = (moduleVideos: Video[]) => {
    const downloadable = moduleVideos.filter(v => v.download_status !== 'done')
    const allSelected = downloadable.every(v => selectedVideoIds.has(v.id))
    const next = new Set(selectedVideoIds)

    downloadable.forEach(v => {
      if (allSelected) next.delete(v.id)
      else next.add(v.id)
    })
    setSelectedVideoIds(next)
  }

  const handleSelectAll = () => {
    const downloadable = videos.filter(v => v.download_status !== 'done')
    if (selectedVideoIds.size === downloadable.length && downloadable.length > 0) {
      setSelectedVideoIds(new Set())
    } else {
      setSelectedVideoIds(new Set(downloadable.map(v => v.id)))
    }
  }

  const handleSave = async () => {
    if (selectedVideoIds.size === 0) {
      toast({ title: "Erro", description: "Selecione pelo menos um vídeo.", variant: "destructive" })
      return
    }

    setSaving(true)
    try {
      const res = await downloadsService.enqueueBatch(Array.from(selectedVideoIds))
      toast({ title: "Sucesso", description: `${res.queued_count} vídeos adicionados à fila.` })
      onEnqueued?.()
      onClose()
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Erro desconhecido"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally {
      setSaving(false)
    }
  }

  const formatDuration = (sec: number) => {
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const formatModuleDuration = (seconds: number): string => {
    if (!seconds || seconds <= 0) return "—"
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0) return `${h}h ${String(m).padStart(2, "0")}min`
    return `${m}min`
  }

  const fmtBytes = (bytes: number | null | undefined): string => {
    if (!bytes || bytes <= 0) return "—"
    const units = ["B", "KB", "MB", "GB", "TB"]
    let value = bytes
    let unitIndex = 0
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024
      unitIndex += 1
    }
    const digits = unitIndex === 0 ? 0 : value < 10 ? 1 : 0
    return `${value.toFixed(digits)} ${units[unitIndex]}`
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-3xl max-h-[85vh] flex flex-col p-6 w-[90vw]">
        <DialogHeader className="mb-4">
          <DialogTitle className="text-xl">Adicionar à Fila de Downloads</DialogTitle>
          <DialogDescription>Selecione a fonte e as aulas específicas que deseja baixar em background.</DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col gap-5">
          <div className="flex flex-col gap-3 shrink-0">
            <label className="text-sm font-medium text-foreground">Origem do Conteúdo</label>
            <Select value={selectedCourseId} onValueChange={(v) => setSelectedCourseId(v || "")} disabled={loadingCourses}>
              <SelectTrigger className="w-full">
                {loadingCourses ? (
                  <span className="text-muted-foreground flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> Carregando...</span>
                ) : selectedLabel ? (
                  <span className="font-semibold">{selectedLabel}</span>
                ) : (
                  <span className="text-muted-foreground">Selecione o curso...</span>
                )}
              </SelectTrigger>
              <SelectContent>
                {courses.map(c => (
                  <SelectItem key={c.id} value={c.id.toString()}>
                    <span className="font-semibold">{c.title}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="border border-border flex-1 flex flex-col overflow-hidden bg-background min-h-[300px]">
            <div className="p-3 border-b border-border bg-muted/20 flex gap-4 items-center shrink-0">
              <div className="flex-1 relative">
                <Search size={14} className="absolute left-2.5 top-2.5 text-muted-foreground" />
                <Input
                  placeholder="Buscar aula ou módulo..."
                  className="pl-8 h-9 text-xs"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
              </div>
              <Button variant="outline" size="sm" className="h-9 text-xs" onClick={handleSelectAll}>
                Selecionar Tudo
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {loadingVideos ? (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  <Loader2 className="animate-spin mr-2" /> Carregando aulas...
                </div>
              ) : modules.length === 0 ? (
                <div className="text-center py-6 text-sm text-muted-foreground">
                  Nenhuma aula encontrada.
                </div>
              ) : (
                <Accordion multiple className="w-full space-y-2">
                  {modules.map(mod => {
                    const downloadable = mod.lessons.filter(v => v.download_status !== 'done')
                    const allSelected = downloadable.length > 0 && downloadable.every(v => selectedVideoIds.has(v.id))
                    const someSelected = downloadable.some(v => selectedVideoIds.has(v.id))
                    const moduleDurationSeconds = mod.lessons.reduce((acc, v) => acc + (v.duration_seconds || 0), 0)
                    const moduleSizeBytes = mod.lessons.reduce((acc, v) => acc + (v.file_size || 0), 0)
                    const moduleDurationStr = formatModuleDuration(moduleDurationSeconds)
                    const moduleSizeStr = fmtBytes(moduleSizeBytes)

                    return (
                      <AccordionItem value={mod.id} key={mod.id} className="border border-border px-3 bg-muted/10 data-[state=open]:bg-transparent">
                        <div className="flex items-center w-full border-b-0">
                          <Checkbox
                            id={`mod-${mod.id}`}
                            className="mr-3 shrink-0"
                            checked={allSelected ? true : (someSelected ? undefined : false)}
                            onCheckedChange={() => toggleModule(mod.lessons)}
                            disabled={downloadable.length === 0}
                          />
                          <AccordionTrigger className="hover:no-underline py-3 flex-1 text-sm font-semibold min-w-0 overflow-hidden">
                            <span className="w-full min-w-0 grid grid-cols-[1fr_auto] items-center gap-3">
                              <span className="text-left truncate min-w-0">
                                {mod.title} ({mod.lessons.length})
                              </span>
                              <span className="text-xs text-muted-foreground font-mono whitespace-nowrap">
                                {moduleDurationStr} · {moduleSizeStr}
                              </span>
                            </span>
                          </AccordionTrigger>
                        </div>
                        <AccordionContent className="pt-1 pb-3 pl-7 space-y-1">
                          {mod.lessons.map(lesson => {
                            const isDone = lesson.download_status === 'done'
                            const isFile = (lesson.media_type ?? "video") !== "video"
                            const sizeStr = fmtBytes(lesson.file_size)
                            const rightText = isFile
                              ? sizeStr
                              : sizeStr !== "—"
                                ? `${formatDuration(lesson.duration_seconds)} · ${sizeStr}`
                                : formatDuration(lesson.duration_seconds)
                            return (
                              <div key={lesson.id} className="flex items-center gap-3 px-2 py-2 hover:bg-muted/40 transition-colors group">
                                <Checkbox
                                  id={`lesson-${lesson.id}`}
                                  checked={selectedVideoIds.has(lesson.id) || isDone}
                                  onCheckedChange={() => toggleVideo(lesson.id)}
                                  disabled={isDone}
                                />
                                <label htmlFor={`lesson-${lesson.id}`} className={`flex-1 flex justify-between items-center ${isDone ? '' : 'cursor-pointer'} ${isDone ? 'opacity-50' : ''}`}>
                                  <span className="text-sm group-hover:text-primary transition-colors flex items-center gap-2">
                                    {lesson.title}
                                    {isDone && <span className="text-[9px] bg-green-500/20 text-green-500 px-1 rounded">Baixado</span>}
                                  </span>
                                  <span className="text-xs text-muted-foreground font-mono">{rightText}</span>
                                </label>
                              </div>
                            )
                          })}
                        </AccordionContent>
                      </AccordionItem>
                    )
                  })}
                </Accordion>
              )}
            </div>
          </div>
        </div>

        <DialogFooter className="shrink-0 pt-4 mt-2">
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button onClick={handleSave} disabled={saving || selectedVideoIds.size === 0}>
            {saving && <Loader2 size={16} className="mr-2 animate-spin" />}
            Adicionar à Fila ({selectedVideoIds.size})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
