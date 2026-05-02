import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { PlayCircle, CheckCircle2, Lock, FileText } from "lucide-react"
import type { Module, Video } from "@/services/courses"
import { useEffect, useMemo, useRef, useState } from "react"

function fmtDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "—"
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, "0")}`
}

function fmtModuleDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}min`
  return `${m}min`
}

function fmtBytes(bytes: number | null | undefined): string {
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

interface ModuleListProps {
  modules: Module[]
  currentVideoId: number | null
  progressPct: number
  onSelect: (video: Video) => void
}

export function ModuleList({ modules, currentVideoId, progressPct, onSelect }: ModuleListProps) {
  const currentModuleName = useMemo(() => {
    if (!currentVideoId) return null
    return modules.find((m) => m.videos.some((v) => v.id === currentVideoId))?.name ?? null
  }, [currentVideoId, modules])

  const initialOpen = useMemo(() => {
    if (currentModuleName) return [currentModuleName]
    return modules[0] ? [modules[0].name] : []
  }, [currentModuleName, modules])

  const [open, setOpen] = useState<string[]>(initialOpen)
  const lastAutoOpenedVideoIdRef = useRef<number | null>(null)

  useEffect(() => {
    if (currentModuleName) {
      if (currentVideoId && lastAutoOpenedVideoIdRef.current !== currentVideoId) {
        setOpen([currentModuleName])
        lastAutoOpenedVideoIdRef.current = currentVideoId
      }
      return
    }
    if (!currentVideoId && !open.length && modules[0]) setOpen([modules[0].name])
  }, [currentVideoId, currentModuleName, modules, open.length])

  return (
    <div className="flex flex-col max-h-[calc(100vh-140px)]">
      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardHeader className="p-4 border-b border-border bg-muted/10 shrink-0">
          <CardTitle className="text-base flex items-center justify-between">
            Conteúdo do Curso
            <span className="text-xs text-muted-foreground font-normal">{progressPct}% concluído</span>
          </CardTitle>
          <Progress value={progressPct} className="h-1.5 mt-3" />
        </CardHeader>

        <div className="flex-1 overflow-y-auto overflow-x-hidden p-2">
          <Accordion multiple value={open} onValueChange={setOpen} className="w-full">
            {modules.map((mod, i) => (
              <AccordionItem
                key={mod.name}
                value={mod.name}
                className="border border-border mb-2 data-[state=open]:bg-muted/5"
              >
                <AccordionTrigger className="px-3 py-3 hover:no-underline gap-3 min-w-0 overflow-hidden">
                  <div className="w-6 h-6 bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold shrink-0">
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div className="flex-1 min-w-0 text-left">
                    <p className="text-xs font-semibold truncate">{mod.name}</p>
                    <p className="text-[10px] text-muted-foreground font-normal mt-0.5 truncate">
                      {mod.total} aulas · {fmtModuleDuration(mod.duration)}
                      {mod.completed > 0 && ` · ${mod.completed}/${mod.total} concluídas`}
                    </p>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-0 pb-0">
                  <div className="flex flex-col">
                    {mod.videos.map((v) => {
                      const isCurrent = v.id === currentVideoId
                      const isAvailable = v.download_status === "done"
                      const isFile = (v.media_type ?? "video") !== "video"
                      const sizeStr = fmtBytes(v.file_size)
                      return (
                        <button
                          key={v.id}
                          type="button"
                          onClick={() => isAvailable && onSelect(v)}
                          disabled={!isAvailable}
                          className={`flex items-start gap-3 px-3 py-2.5 text-left transition-colors border-t border-border w-full
                            ${isCurrent ? "bg-primary/10 border-l-2 border-l-primary" : "border-l-2 border-l-transparent"}
                            ${isAvailable ? "cursor-pointer hover:bg-accent/50" : "cursor-not-allowed opacity-50"}
                          `}
                        >
                          <div className="mt-0.5 shrink-0">
                            {isCurrent && v.completed ? (
                              <CheckCircle2 size={14} className="text-primary" />
                            ) : isCurrent ? (
                              <div className="relative flex h-3 w-3">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                                <span className="relative inline-flex rounded-full h-3 w-3 bg-primary" />
                              </div>
                            ) : v.completed ? (
                              <CheckCircle2 size={14} className="text-green-400" />
                            ) : !isAvailable ? (
                              <Lock size={14} className="text-muted-foreground/40" />
                            ) : isFile ? (
                              <FileText size={14} className="text-muted-foreground/60" />
                            ) : (
                              <PlayCircle size={14} className="text-muted-foreground/40" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p
                              className={`text-xs truncate ${
                                v.completed && !isCurrent
                                  ? "text-muted-foreground"
                                  : isCurrent
                                  ? "text-foreground font-medium"
                                  : ""
                              }`}
                            >
                              {v.title}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-[10px] text-muted-foreground/60 font-mono">
                                {v.fcode}
                              </span>
                              <span className="text-[10px] text-muted-foreground">
                                {isFile ? sizeStr : fmtDuration(v.duration_seconds)}
                              </span>
                              {!isFile && (
                                <span className="text-[10px] text-muted-foreground/60">
                                  · {sizeStr}
                                </span>
                              )}
                              {!isAvailable && (
                                <span className="text-[10px] text-muted-foreground/60">
                                  · não baixado
                                </span>
                              )}
                            </div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </Card>
    </div>
  )
}
