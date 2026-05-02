import { useEffect, useState } from "react"
import { NavLink, useNavigate } from "react-router-dom"
import { LayoutDashboard, BookOpen, Download, Settings, Terminal, LogOut } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useAuth } from "@/contexts/auth"
import { coursesService } from "@/services/courses"
import { downloadsService } from "@/services/downloads"

export default function Sidebar({ className }: { className?: string }) {
  const { name, email, logout } = useAuth()
  const navigate = useNavigate()
  const initials = name ? name.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase() : "?"

  const [courseCount, setCourseCount] = useState<number | null>(null)
  const [activeDownloads, setActiveDownloads] = useState<number | null>(null)

  useEffect(() => {
    coursesService.list().then(data => setCourseCount(data.length)).catch(() => {})
  }, [])

  useEffect(() => {
    const fetch = () =>
      downloadsService.status().then(data => {
        const count = data.jobs.filter(j => j.status === "pending" || j.status === "downloading" || j.status === "retry_pending").length
        setActiveDownloads(count)
      }).catch(() => {})
    fetch()
    const interval = setInterval(fetch, 5000)
    return () => clearInterval(interval)
  }, [])

  const nav = [
    { to: "/dashboard",  icon: LayoutDashboard, label: "Dashboard",  badge: null },
    { to: "/courses",    icon: BookOpen,        label: "Cursos",     badge: courseCount },
    { to: "/downloads",  icon: Download,        label: "Downloads",  badge: activeDownloads },
    { to: "/management", icon: Settings,        label: "Gerenciar",  badge: null },
  ]

  return (
    <aside className={cn("flex flex-col h-full w-[248px] border-r border-border bg-card shrink-0", className)}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-border">
        <div className="w-9 h-9 bg-primary flex items-center justify-center shrink-0">
          <Terminal size={16} className="text-primary-foreground" />
        </div>
        <div>
          <p className="text-xs font-semibold leading-tight">AulaFlow</p>
          <p className="text-[11px] text-muted-foreground">Pro 2.0</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 pt-4 space-y-0.5 overflow-y-auto">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50 px-2 pb-2">
          Menu
        </p>
        {nav.map(({ to, icon: Icon, label, badge }) => (
          <NavLink
            key={label}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 px-3 py-2.5 text-xs font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )
            }
          >
            <Icon size={15} className="shrink-0" />
            <span className="flex-1">{label}</span>
            {badge !== null && badge !== undefined && (
              <Badge variant="default" className="text-[10px] min-w-[18px] justify-center">
                {badge}
              </Badge>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-border">
        <div className="flex items-center gap-2.5 px-3 py-2.5 hover:bg-accent transition-colors">
          <Avatar>
            <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold truncate">{name ?? "—"}</p>
            <p className="text-[11px] text-muted-foreground truncate">{email ?? "—"}</p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground"
            onClick={() => {
              logout()
              navigate("/login", { replace: true })
            }}
            title="Sair"
          >
            <LogOut size={16} />
          </Button>
        </div>
      </div>
    </aside>
  )
}
