import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { SYSTEM_SERVICE_ICON_MAP } from "@/constants/management"
import { managementService } from "@/services/management"
import type { SystemHealth } from "@/services/management"
import { Loader2 } from "lucide-react"

export function SystemStatus() {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await managementService.getSystemHealth()
        setHealth(data)
      } catch (error) {
        console.error("Failed to fetch system health", error)
      } finally {
        setLoading(false)
      }
    }
    
    fetchHealth()
    const interval = setInterval(fetchHealth, 30000) // update every 30s
    return () => clearInterval(interval)
  }, [])

  if (loading && !health) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Status do Sistema</CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  const services = [
    { 
      label: "PostgreSQL", 
      status: health?.postgres ? "Online" : "Offline", 
      color: health?.postgres ? "text-green-400" : "text-red-400", 
      bg: health?.postgres ? "bg-green-400/10" : "bg-red-400/10", 
      icon: "Database" 
    },
    { 
      label: "SeaweedFS", 
      status: health?.seaweed ? "Online" : "Offline", 
      color: health?.seaweed ? "text-green-400" : "text-red-400", 
      bg: health?.seaweed ? "bg-green-400/10" : "bg-red-400/10", 
      icon: "HardDrive" 
    },
  ]

  const storagePercent = health && health.storage_total_gb > 0 
    ? (health.storage_used_gb / health.storage_total_gb) * 100 
    : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>Status do Sistema</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {services.map(({ label, status, color, bg, icon }) => {
          const Icon = SYSTEM_SERVICE_ICON_MAP[icon as keyof typeof SYSTEM_SERVICE_ICON_MAP]
          return (
            <div key={label} className="flex items-center gap-3 p-3 bg-background border border-border">
              <div className={`w-8 h-8 flex items-center justify-center ${bg} ${color}`}>
                <Icon size={15} />
              </div>
              <p className="flex-1 text-xs font-medium">{label}</p>
              <span className={`text-xs font-semibold ${color}`}>{status}</span>
            </div>
          )
        })}

        <div className="p-3 bg-background border border-border mt-4">
          <Progress value={storagePercent}>
            <span className="text-xs text-muted-foreground">Armazenamento usado</span>
            <span className="ml-auto text-xs font-semibold tabular-nums">
              {health?.storage_used_gb || 0} GB / {health?.storage_total_gb || 0} GB
            </span>
          </Progress>
        </div>
      </CardContent>
    </Card>
  )
}
