import { Wifi, Database, HardDrive } from "lucide-react"

export const SYSTEM_SERVICE_ICON_MAP = { Wifi, Database, HardDrive }

export const INTEGRATIONS = [
  { id: 1, platform: "Telegram", name: "DevOps Pro 2", type: "Canal", status: "active" },
  { id: 2, platform: "Telegram", name: "SRE Foundations", type: "Canal", status: "active" },
]

export const SYSTEM_SERVICES = [
  { label: "Telegram API", status: "Online",  color: "text-green-400", bg: "bg-green-400/10", icon: "Wifi" },
  { label: "PostgreSQL",   status: "Online",  color: "text-green-400", bg: "bg-green-400/10", icon: "Database" },
  { label: "SeaweedFS",    status: "Offline", color: "text-red-400",   bg: "bg-red-400/10",   icon: "HardDrive" },
] as const

export const STORAGE_USED_PERCENT = 23.6
export const STORAGE_LABEL = "47.2 GB / 200 GB"
