import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react"
import { api } from "@/lib/api"

interface AuthState {
  token: string | null
  userId: number | null
  name: string | null
  email: string | null
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>
  register: (email: string, name: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

function setTokenCookie(token: string) {
  document.cookie = `token=${encodeURIComponent(token)}; Path=/; SameSite=Lax`
}

function clearTokenCookie() {
  document.cookie = "token=; Path=/; Max-Age=0; SameSite=Lax"
}

function parseTokenPayload(token: string): { user_id: number } | null {
  try {
    const payload = token.split(".")[1]
    return JSON.parse(atob(payload))
  } catch {
    return null
  }
}

function loadInitial(): AuthState {
  const token = localStorage.getItem("token")
  if (!token) return { token: null, userId: null, name: null, email: null }
  const payload = parseTokenPayload(token)
  if (!payload) return { token: null, userId: null, name: null, email: null }
  return {
    token,
    userId: payload.user_id,
    name: localStorage.getItem("user_name"),
    email: localStorage.getItem("user_email"),
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(loadInitial)

  useEffect(() => {
    if (state.token) setTokenCookie(state.token)
    else clearTokenCookie()
  }, [state.token])

  useEffect(() => {
    if (!state.token) return
    let cancelled = false
    api.get<{ id: number; email: string; name: string }>("/auth/me")
      .then(user => {
        if (cancelled) return
        localStorage.setItem("user_name", user.name)
        localStorage.setItem("user_email", user.email)
        setState(s => ({ ...s, userId: user.id, name: user.name, email: user.email }))
      })
      .catch(() => {
        if (cancelled) return
        localStorage.removeItem("token")
        localStorage.removeItem("user_name")
        localStorage.removeItem("user_email")
        clearTokenCookie()
        setState({ token: null, userId: null, name: null, email: null })
      })
    return () => {
      cancelled = true
    }
  }, [state.token])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.postForm<{ access_token: string }>("/auth/login", {
      username: email,
      password,
    })
    localStorage.setItem("token", res.access_token)
    setTokenCookie(res.access_token)
    const payload = parseTokenPayload(res.access_token)
    const user = await api.get<{ id: number; email: string; name: string }>("/auth/me")
    localStorage.setItem("user_name", user.name)
    localStorage.setItem("user_email", user.email)
    setState({ token: res.access_token, userId: payload?.user_id ?? null, name: user.name, email: user.email })
  }, [])

  const register = useCallback(async (email: string, name: string, password: string) => {
    await api.post("/auth/register", { email, name, password })
    await login(email, password)
  }, [login])

  const logout = useCallback(() => {
    localStorage.removeItem("token")
    localStorage.removeItem("user_name")
    localStorage.removeItem("user_email")
    clearTokenCookie()
    setState({ token: null, userId: null, name: null, email: null })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, isAuthenticated: !!state.token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider")
  return ctx
}
