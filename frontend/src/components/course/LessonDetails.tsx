import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { Video } from "@/services/courses"

interface LessonDetailsProps {
  video: Video
  moduleIndex: number
  totalModules: number
  description?: string | null
}

export function LessonDetails({ video, moduleIndex, totalModules, description }: LessonDetailsProps) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between mb-2">
          <Badge variant="outline" className="text-primary border-primary/30 bg-primary/5">
            {video.module_name}
          </Badge>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">Módulo {moduleIndex}/{totalModules}</Badge>
            <Badge variant="secondary">Aula {video.order_index}</Badge>
            <span className="text-xs text-muted-foreground font-mono">{video.fcode}</span>
          </div>
        </div>
        <CardTitle className="text-2xl">{video.title}</CardTitle>
        {description && <CardDescription className="text-sm mt-2">{description}</CardDescription>}
      </CardHeader>
    </Card>
  )
}
