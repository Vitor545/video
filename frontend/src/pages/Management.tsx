import { useState } from "react"
import AppLayout from "@/components/layout/AppLayout"
import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"
import { IntegrationList } from "@/components/management/IntegrationList"
import { SystemStatus } from "@/components/management/SystemStatus"
import { NewIntegrationModal } from "@/components/management/NewIntegrationModal"

export default function Management() {
  const [isAddingNew, setIsAddingNew] = useState(false)

  return (
    <AppLayout
      title="Gerenciamento"
      subtitle="Gerencie suas integrações e fontes de dados"
      actions={
        <Button onClick={() => setIsAddingNew(true)}>
          <Plus size={14} className="mr-1" /> Nova Integração
        </Button>
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-5 mb-5">
        <IntegrationList />
        <SystemStatus />
      </div>

      <NewIntegrationModal open={isAddingNew} onClose={() => setIsAddingNew(false)} />
    </AppLayout>
  )
}
