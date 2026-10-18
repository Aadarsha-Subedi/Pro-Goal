import { useEffect, useState } from "react"
import { BootScreen } from "@/components/patterns/boot-screen"

/** Set by the router when a page resolves: true while the person is outside the signed-in app. */
let outsideApp = true
export const setOutsideApp = (value: boolean) => { outsideApp = value }

const SLOW_AFTER_MS = 25000

/**
 * What shows while a route loads. A refresh, a reload and the first step into the app get the boot screen
 * (it fades in after a moment, so fast loads never flash it). Moving between pages inside the app stays quiet.
 */
export function RouterPending() {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const t = window.setTimeout(() => setSlow(true), SLOW_AFTER_MS)
    return () => window.clearTimeout(t)
  }, [])
  if (!outsideApp) return <div className="min-h-screen" aria-busy="true" />
  return <BootScreen message="Loading Pro-Goal" slow={slow} onRetry={() => window.location.reload()} />
}
