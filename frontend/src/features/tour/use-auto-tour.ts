import { useRouter } from "@tanstack/react-router"
import { useEffect, useRef } from "react"
import { authApi } from "@/features/auth/api"
import { startTour, stopTour } from "./tour"

/** Starts the walkthrough once for a signed-in user who has not seen it, as soon as its targets are on screen. Finishing or skipping saves that, so it never runs again on its own. */
export function useAutoTour(enabled: boolean) {
  const router = useRouter()
  const started = useRef(false)
  useEffect(() => {
    if (!enabled || started.current) return
    // Let the shell and page paint first so the targets exist and have a size.
    const timer = window.setTimeout(() => {
      const shown = startTour(() => {
        authApi.finishTour().then(() => router.invalidate()).catch(() => {})
      })
      if (shown) started.current = true
    }, 600)
    return () => {
      window.clearTimeout(timer)
    }
  }, [enabled, router])
  useEffect(() => () => stopTour(), [])
}
