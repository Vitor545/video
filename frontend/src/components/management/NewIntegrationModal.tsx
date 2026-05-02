import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { managementService } from "@/services/management"
import { useToast } from "@/hooks/use-toast"
import { Loader2 } from "lucide-react"

type Props = {
  open: boolean
  onClose: () => void
}

export function NewIntegrationModal({ open, onClose }: Props) {
  const [name, setName] = useState("")
  const [channel, setChannel] = useState("")
  const [saving, setSaving] = useState(false)
  
  const { toast } = useToast()

  const handleSave = async () => {
    if (!name || !channel) {
      toast({ title: "Erro", description: "Preencha todos os campos obrigatórios.", variant: "destructive" })
      return
    }

    setSaving(true)
    try {
      await managementService.createIntegration({
        name,
        channel_name: channel,
        auto_sync: true
      })
      toast({ title: "Sucesso", description: "Integração salva e extração iniciada." })
      // Reset form
      setName("")
      setChannel("")
      
      onClose()
      // Note: O componente pai ou a lista deve ser notificado para recarregar. 
      // O IntegrationList usa polling, então ele vai pegar a nova logo depois.
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Erro desconhecido"
      toast({ title: "Erro", description: msg, variant: "destructive" })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-2xl w-[90vw] p-6">
        <DialogHeader className="mb-4">
          <DialogTitle className="text-xl">Nova Integração: Telegram</DialogTitle>
            <DialogDescription className="mt-1">Conecte um novo canal para importar um curso.</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 py-4">
          <div className="space-y-2">
            <Label htmlFor="name" className="text-foreground">Nome da Integração *</Label>
            <Input id="name" placeholder="Ex: DevOps Pro 2" value={name} onChange={e => setName(e.target.value)} disabled={saving} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="channel" className="text-foreground">Nome / Link do Canal *</Label>
            <Input id="channel" placeholder="Ex: @devopspro2" value={channel} onChange={e => setChannel(e.target.value)} disabled={saving} />
          </div>
        </div>

        <DialogFooter className="mt-4 pt-4 border-t border-border">
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancelar</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Loader2 size={16} className="mr-2 animate-spin" />}
            Salvar e Conectar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
