import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Terminal, Eye, EyeOff } from "lucide-react"
import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useAuth } from "@/contexts/auth"
import { toast } from "sonner"

export default function Register() {
  const [show, setShow] = useState(false)
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (password !== confirm) {
      toast.error("As senhas não coincidem")
      return
    }
    setLoading(true)
    try {
      await register(email, name, password)
      navigate("/dashboard", { replace: true })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao criar conta")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen bg-background flex items-center justify-center"
      style={{
        backgroundImage:
          "radial-gradient(ellipse at 20% 50%, hsl(var(--primary)/.06) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, hsl(var(--primary)/.03) 0%, transparent 60%)",
      }}
    >
      <div className="w-[400px] bg-card ring-1 ring-foreground/10 p-10">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-11 h-11 bg-primary flex items-center justify-center shrink-0">
            <Terminal size={20} className="text-primary-foreground" />
          </div>
          <div>
            <p className="text-sm font-bold leading-tight">AulaFlow</p>
            <p className="text-xs text-muted-foreground">Área do aluno</p>
          </div>
        </div>

        <h2 className="text-xl font-bold mb-1">Criar conta</h2>
        <p className="text-xs text-muted-foreground mb-7">Preencha os dados para acessar a plataforma</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="name">Nome</Label>
            <Input
              id="name"
              type="text"
              placeholder="Seu nome"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Senha</Label>
            <div className="relative">
              <Input
                id="password"
                type={show ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pr-9"
                required
              />
              <button
                type="button"
                onClick={() => setShow(s => !s)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                {show ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="confirm">Confirmar senha</Label>
            <Input
              id="confirm"
              type={show ? "text" : "password"}
              placeholder="••••••••"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>

          <Button type="submit" className="w-full mt-1" disabled={loading}>
            {loading ? "Criando conta..." : "Criar conta"}
          </Button>
        </form>

        <p className="text-center text-xs text-muted-foreground mt-6">
          Já tem conta?{" "}
          <Link to="/login" className="text-primary hover:underline">Entrar</Link>
        </p>
      </div>
    </div>
  )
}
