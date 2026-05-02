import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { MoreVertical, RefreshCw, Send, Loader2, KeyRound } from "lucide-react"
import type { Integration } from "@/services/management"
import { managementService } from "@/services/management"
import { Progress } from "@/components/ui/progress"
import { useToast } from "@/hooks/use-toast"

export function IntegrationList() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [syncingAll, setSyncingAll] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)
  const [authStep, setAuthStep] = useState<"idle" | "sending" | "waiting_code" | "verifying">("idle")
  const [authCode, setAuthCode] = useState("")
  const { toast } = useToast()

  const fetchIntegrations = async () => {
    try {
      const data = await managementService.getIntegrations()
      setIntegrations(data)
    } catch (error) {
      console.error("Failed to fetch integrations", error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchIntegrations()
    const interval = setInterval(fetchIntegrations, 3000) // fast polling for sync progress
    return () => clearInterval(interval)
  }, [])

  const handleSyncAll = async () => {
    setSyncingAll(true)
    try {
      const res = await managementService.syncAll()
      toast({ title: "Sincronização Iniciada", description: res.message })
      fetchIntegrations()
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Erro desconhecido"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally {
      setSyncingAll(false)
    }
  }

  const handleSendCode = async () => {
    setAuthOpen(true)
    setAuthStep("sending")
    setAuthCode("")
    try {
      const res = await managementService.telegramSendCode()
      toast({ title: "Código enviado", description: res.detail })
      setAuthStep("waiting_code")
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Erro ao enviar código"
      toast({ title: "Erro", description: msg, variant: "destructive" })
      setAuthStep("idle")
      setAuthOpen(false)
    }
  }

  const handleVerifyCode = async () => {
    setAuthStep("verifying")
    try {
      const res = await managementService.telegramVerifyCode(authCode)
      toast({ title: "Autenticado!", description: res.detail })
      setAuthOpen(false)
      setAuthStep("idle")
      setAuthCode("")
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Código inválido"
      toast({ title: "Erro", description: msg, variant: "destructive" })
      setAuthStep("waiting_code")
    }
  }

  const handleSyncSingle = async (id: number) => {
    try {
      await managementService.syncIntegration(id)
      toast({ title: "Sincronização Iniciada", description: "A extração foi colocada na fila." })
      fetchIntegrations()
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Erro desconhecido"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    }
  }

  if (loading && integrations.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Integrações Ativas</CardTitle>
          <CardDescription>Gerencie de onde seus cursos estão sendo importados.</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Integrações Ativas</CardTitle>
        <CardDescription>Gerencie de onde seus cursos estão sendo importados.</CardDescription>
        <CardAction>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleSendCode} disabled={authStep !== "idle"}>
              {authStep === "sending" ? <Loader2 size={14} className="mr-2 animate-spin" /> : <KeyRound size={14} className="mr-2" />}
              Auth
            </Button>
            <Button variant="outline" size="sm" onClick={handleSyncAll} disabled={syncingAll || integrations.length === 0}>
              {syncingAll ? <Loader2 size={14} className="mr-2 animate-spin" /> : <RefreshCw size={14} className="mr-2" />}
              Sincronizar Tudo
            </Button>
          </div>
        </CardAction>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {integrations.length === 0 ? (
            <div className="text-center py-6 text-sm text-muted-foreground border border-dashed border-border">
              Nenhuma integração configurada.
            </div>
          ) : (
            integrations.map(integ => {
              const isSyncing = integ.sync_status && ["collecting", "extracting", "importing"].includes(integ.sync_status.phase)
              const syncPercent = integ.sync_status?.total ? (integ.sync_status.progress / integ.sync_status.total) * 100 : 0

              let phaseLabel = ""
              if (integ.sync_status?.phase === "collecting") phaseLabel = "Coletando mensagens..."
              if (integ.sync_status?.phase === "extracting") phaseLabel = "Extraindo IA..."
              if (integ.sync_status?.phase === "importing") phaseLabel = "Importando..."

              return (
                <div key={integ.id} className="flex flex-col border border-border bg-background transition-colors hover:border-primary/30">
                  <div className="flex items-center gap-4 p-4">
                    <div className="w-10 h-10 bg-muted flex items-center justify-center shrink-0">
                      <Send size={16} className="text-[#0088cc]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-sm font-semibold truncate">{integ.name || integ.channel_name}</p>
                        {integ.is_active
                          ? <Badge variant="outline" className="text-green-400 border-green-400/30 text-[9px] h-4 leading-none px-1.5 py-0">Online</Badge>
                          : <Badge variant="destructive" className="text-[9px] h-4 leading-none px-1.5 py-0">Offline</Badge>
                        }
                      </div>
                      <p className="text-[11px] text-muted-foreground font-mono">Telegram · Canal: {integ.channel_name}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {!isSyncing && (
                        <>
                          <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => handleSyncSingle(integ.id)}>
                            Sincronizar
                          </Button>
                        </>
                      )}
                      <Button variant="ghost" size="icon" className="shrink-0 text-muted-foreground h-8 w-8">
                        <MoreVertical size={16} />
                      </Button>
                    </div>
                  </div>

                  {/* Progress Bar para Sync */}
                  {isSyncing && (
                    <div className="px-4 pb-3 pt-0">
                      <div className="flex justify-between text-[10px] mb-1">
                        <span className="text-muted-foreground">{phaseLabel}</span>
                        <span className="font-mono">{integ.sync_status?.progress} / {integ.sync_status?.total}</span>
                      </div>
                      <Progress value={syncPercent} className="h-1.5" />
                    </div>
                  )}
                  {integ.sync_status?.phase === "error" && (
                    <div className="px-4 pb-3 pt-0 text-xs text-destructive">
                      Erro na sincronização: {integ.sync_status.error}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </CardContent>

      {/* Dialog de autenticação Telegram */}
      <Dialog open={authOpen} onOpenChange={(o) => { if (!o) { setAuthOpen(false); setAuthStep("idle"); setAuthCode("") } }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Autenticar Telegram</DialogTitle>
            <DialogDescription>
              {authStep === "waiting_code" || authStep === "verifying"
                ? "Insira o código enviado pelo Telegram"
                : "Enviando código..."}
            </DialogDescription>
          </DialogHeader>
          {(authStep === "waiting_code" || authStep === "verifying") && (
            <Input
              placeholder="Ex: 12345"
              value={authCode}
              onChange={e => setAuthCode(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleVerifyCode()}
              autoFocus
            />
          )}
          <DialogFooter>
            {authStep === "sending" && <Loader2 className="animate-spin text-muted-foreground" />}
            {(authStep === "waiting_code" || authStep === "verifying") && (
              <Button onClick={handleVerifyCode} disabled={authStep === "verifying" || !authCode}>
                {authStep === "verifying" ? <Loader2 size={14} className="mr-2 animate-spin" /> : null}
                Verificar
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
