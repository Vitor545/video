import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { CheckCircle2, HardDrive, Trash2, Loader2 } from "lucide-react"
import { downloadsService } from "@/services/downloads"
import type { StatusResponse, DownloadJob } from "@/services/downloads"
import { useToast } from "@/hooks/use-toast"

export function DownloadedStorage() {
  const [data, setData] = useState<StatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [deletingCourseId, setDeletingCourseId] = useState<number | null>(null)
  const [deletingVideoId, setDeletingVideoId] = useState<number | null>(null)
  const { toast } = useToast()

  const fetchStatus = async () => {
    try {
      const res = await downloadsService.status()
      setData(res)
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Poll slower for downloaded tab
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleDeleteCourse = async (e: React.MouseEvent, courseId: number) => {
    e.stopPropagation()
    if (!confirm("Tem certeza que deseja apagar todos os vídeos deste curso do storage local?")) return

    setDeletingCourseId(courseId)
    try {
      await downloadsService.deleteCourseStorage(courseId)
      toast({ title: "Curso limpo com sucesso" })
      fetchStatus()
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Erro desconhecido"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally {
      setDeletingCourseId(null)
    }
  }

  const handleDeleteVideo = async (videoId: number) => {
    if (!confirm("Tem certeza que deseja apagar este vídeo do storage local?")) return

    setDeletingVideoId(videoId)
    try {
      await downloadsService.deleteVideoStorage(videoId)
      toast({ title: "Vídeo apagado com sucesso" })
      fetchStatus()
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Erro desconhecido"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally {
      setDeletingVideoId(null)
    }
  }

  if (loading && !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Armazenamento Local</CardTitle>
          <CardDescription>Carregando arquivos...</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  const doneJobs = data?.jobs.filter(j => j.status === "done") || []

  // Group by course
  const grouped: Record<number, { title: string, jobs: DownloadJob[], totalBytes: number }> = {}

  doneJobs.forEach(job => {
    const cid = job.course_id || 0
    if (!grouped[cid]) {
      grouped[cid] = {
        title: job.course_title || `Curso ${cid}`,
        jobs: [],
        totalBytes: 0
      }
    }
    grouped[cid].jobs.push(job)
    grouped[cid].totalBytes += (job.file_size || 0)
  })

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (isoString: string | null) => {
    if (!isoString) return ""
    const d = new Date(isoString)
    return d.toLocaleDateString("pt-BR")
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Armazenamento Local</CardTitle>
        <CardDescription>Gerencie as aulas que já foram baixadas no servidor.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {Object.keys(grouped).length === 0 ? (
          <div className="text-center py-6 text-sm text-muted-foreground border border-dashed border-border">
            Nenhum vídeo no armazenamento local.
          </div>
        ) : (
          <Accordion multiple className="w-full space-y-4">
            {Object.entries(grouped).map(([courseId, group]) => (
              <AccordionItem key={courseId} value={courseId} className="border border-border bg-background hover:border-primary/20 transition-colors">
                <AccordionTrigger className="hover:no-underline px-4 py-3 items-center">
                  <div className="flex items-center gap-3 text-left w-full pr-2">
                    <div className="w-9 h-9 bg-primary/10 flex items-center justify-center shrink-0">
                      <HardDrive size={16} className="text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-sm leading-tight truncate">{group.title}</h3>
                      <p className="text-xs text-muted-foreground font-normal mt-0.5 m-0">
                        {group.jobs.length} aulas · {formatBytes(group.totalBytes)}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 h-8 px-2 shrink-0 relative z-10"
                      onClick={(e) => handleDeleteCourse(e, parseInt(courseId))}
                      disabled={deletingCourseId === parseInt(courseId)}
                    >
                      {deletingCourseId === parseInt(courseId) ? (
                        <Loader2 size={14} className="sm:mr-1.5 animate-spin" />
                      ) : (
                        <Trash2 size={14} className="sm:mr-1.5" />
                      )}
                      <span className="hidden sm:inline">Limpar Curso</span>
                    </Button>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4 pt-2 border-t border-border bg-muted/10">
                  <div className="space-y-1 mt-2">
                    {group.jobs.map(job => (
                      <div key={job.id} className="group flex items-center justify-between p-2 hover:bg-accent transition-colors">
                        <div className="flex items-center gap-3 min-w-0">
                          <CheckCircle2 size={14} className="text-primary shrink-0" />
                          <div className="min-w-0">
                            <div className="text-xs font-medium truncate">{job.video_title}</div>
                            <div className="text-[10px] text-muted-foreground truncate mt-0.5">
                              {job.module_name || "Módulo"} · Video {job.video_id}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 shrink-0 pl-3">
                          <div className="text-right">
                            <div className="text-[10px] font-mono font-medium">{formatBytes(job.file_size || 0)}</div>
                            <div className="text-[9px] text-muted-foreground">{formatDate(job.finished_at)}</div>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={() => handleDeleteVideo(job.video_id)}
                            disabled={deletingVideoId === job.video_id}
                          >
                            {deletingVideoId === job.video_id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
      </CardContent>
    </Card>
  )
}
