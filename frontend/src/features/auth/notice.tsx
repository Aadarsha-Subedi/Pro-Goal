import type { ReactNode } from "react"
import { CheckCircle, Info, Warning, XCircle } from "@/icons"

const TONES = {
  info: { Icon: Info, cls: "text-info" },
  success: { Icon: CheckCircle, cls: "text-success" },
  warning: { Icon: Warning, cls: "text-warning" },
  danger: { Icon: XCircle, cls: "text-destructive" },
} as const

/** Flat notice row: filled icon in the state color, title and one sentence. */
export function Notice({ tone, title, children, action }: { tone: keyof typeof TONES; title: string; children?: ReactNode; action?: ReactNode }) {
  const { Icon, cls } = TONES[tone]
  return (
    <div role={tone === "danger" ? "alert" : "status"} className="flex gap-2.5 border-y bp-rule py-3 text-sm">
      <Icon weight="fill" className={`mt-0.5 size-4 shrink-0 ${cls}`} aria-hidden />
      <div className="min-w-0">
        <p className="font-medium">{title}</p>
        {children && <p className="bp-muted">{children}</p>}
        {action && <div className="mt-2">{action}</div>}
      </div>
    </div>
  )
}
