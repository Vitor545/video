export const COLOR_SCHEME_QUERY = "(prefers-color-scheme: dark)"
export const THEME_VALUES = ["dark", "light", "system"] as const

export type Theme = "dark" | "light" | "system"
export type ResolvedTheme = "dark" | "light"

export function isTheme(value: string | null): value is Theme {
  if (value === null) return false
  return (THEME_VALUES as readonly string[]).includes(value)
}

export function getSystemTheme(): ResolvedTheme {
  return window.matchMedia(COLOR_SCHEME_QUERY).matches ? "dark" : "light"
}

export function disableTransitionsTemporarily() {
  const style = document.createElement("style")
  style.appendChild(
    document.createTextNode(
      "*,*::before,*::after{-webkit-transition:none!important;transition:none!important}"
    )
  )
  document.head.appendChild(style)

  return () => {
    window.getComputedStyle(document.body)
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        style.remove()
      })
    })
  }
}

export function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  return !!target.closest("input, textarea, select, [contenteditable='true']")
}
