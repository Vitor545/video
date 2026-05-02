import AppLayout from "@/components/layout/AppLayout"
import { useAuth } from "@/contexts/auth"
import { useState } from "react"
import { StatCards } from "@/components/dashboard/StatCards"
import { WeeklyChart } from "@/components/dashboard/WeeklyChart"
import { ModuleRadialChart } from "@/components/dashboard/ModuleRadialChart"
import { StreakChart } from "@/components/dashboard/StreakChart"
import { HourlyChart } from "@/components/dashboard/HourlyChart"
import { RecentVideos } from "@/components/dashboard/RecentVideos"
import { MyCourses } from "@/components/dashboard/MyCourses"
import { useFetch } from "@/hooks/useFetch"
import { dashboardService } from "@/services/dashboard"

export default function Dashboard() {
  const { name } = useAuth()
  const [courseValue, setCourseValue] = useState<string>("all")
  const courseId = courseValue === "all" ? null : Number(courseValue)
  const { data: myCourses } = useFetch(() => dashboardService.myCourses(), [])
  return (
    <AppLayout title="Dashboard" subtitle={`Bem-vindo de volta, ${name ?? ""}`.trimEnd()}>
      <div className="mb-5">
        <RecentVideos />
      </div>

      <StatCards
        courses={myCourses ?? []}
        courseValue={courseValue}
        onCourseValueChange={setCourseValue}
        courseId={courseId}
      />

      <div className="mb-5">
        <WeeklyChart courseId={courseId} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
        <StreakChart courseId={courseId} />
        <HourlyChart courseId={courseId} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5 mb-5">
        <MyCourses />
        <ModuleRadialChart courseId={courseId} />
      </div>
    </AppLayout>
  )
}
