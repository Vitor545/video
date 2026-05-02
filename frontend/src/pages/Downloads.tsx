import { useState } from "react"
import AppLayout from "@/components/layout/AppLayout"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Plus } from "lucide-react"
import { DownloadQueue } from "@/components/downloads/DownloadQueue"
import { DownloadedStorage } from "@/components/downloads/DownloadedStorage"
import { ModuleDownloadChart } from "@/components/downloads/ModuleDownloadChart"
import { AddDownloadModal } from "@/components/downloads/AddDownloadModal"

export default function Downloads() {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [tab, setTab] = useState<"queue" | "downloaded">("queue")
  const [refreshToken, setRefreshToken] = useState(0)

  return (
    <AppLayout title="Downloads" subtitle="Controle e acompanhamento de downloads">
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-5">

        <div className="flex flex-col">
          <Tabs value={tab} onValueChange={(v) => setTab(v as "queue" | "downloaded")} className="w-full flex-1 flex flex-col">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <TabsList className="w-full sm:w-auto grid grid-cols-2 sm:flex">
                <TabsTrigger value="queue">Fila</TabsTrigger>
                <TabsTrigger value="downloaded">Baixados</TabsTrigger>
              </TabsList>
              <Button size="sm" onClick={() => setIsAddModalOpen(true)} className="w-full sm:w-auto">
                <Plus size={14} className="mr-1" /> Adicionar Download
              </Button>
            </div>

            <TabsContent value="queue" className="mt-0 flex-1">
              <DownloadQueue refreshToken={refreshToken} />
            </TabsContent>
            <TabsContent value="downloaded" className="mt-0 flex-1">
              <DownloadedStorage />
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-5">
          <ModuleDownloadChart />
        </div>
      </div>

      <AddDownloadModal
        open={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onEnqueued={() => {
          setTab("queue")
          setRefreshToken((n) => n + 1)
        }}
      />
    </AppLayout>
  )
}
