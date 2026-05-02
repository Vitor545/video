import type { ReactNode } from "react"
import Sidebar from "./Sidebar"
import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet"

interface Props {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
}

export default function AppLayout({ title, subtitle, actions, children }: Props) {
  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <div className="hidden md:block sticky top-0 h-screen">
        <Sidebar className="border-r border-border h-full" />
      </div>

      <div className="flex flex-col flex-1 min-w-0">
        {/* Topbar */}
        <header className="h-16 border-b border-border bg-card flex items-center px-4 md:px-8 gap-4 shrink-0 sticky top-0 z-20">
          <Sheet>
            <SheetTrigger>
              <Button variant="ghost" size="icon" className="md:hidden shrink-0">
                <Menu size={20} />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="p-0 w-[248px] border-border border-r">
              <SheetTitle className="sr-only">Menu</SheetTitle>
              <Sidebar className="border-0 w-full" />
            </SheetContent>
          </Sheet>
          
          <div className="flex-1 min-w-0">
            <h1 className="text-[15px] font-semibold truncate">{title}</h1>
            {subtitle && <p className="text-[12px] text-muted-foreground truncate">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2 md:gap-3 shrink-0 overflow-x-auto">{actions}</div>}
        </header>

        {/* Content */}
        <main className="flex-1 p-4 md:p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}
