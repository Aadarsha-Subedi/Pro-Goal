import { driver, type DriveStep } from "driver.js"
import "driver.js/dist/driver.css"
import "./tour.css"
import { availableSteps } from "./steps"

let active: ReturnType<typeof driver> | null = null
let ended: (() => void) | undefined

/** Highlights each visible target in turn with Next, Back and Skip. Returns false when no target is on screen. `onEnd` runs once, whether the user finished or skipped. */
export function startTour(onEnd?: () => void): boolean {
  if (active) return true
  ended = onEnd
  const steps: DriveStep[] = availableSteps().map((s) => ({
    element: `[data-tour="${s.target}"]`,
    popover: { title: s.title, description: s.description, side: s.side },
  }))
  if (steps.length === 0) return false
  active = driver({
    steps,
    showProgress: true,
    progressText: "{{current}} of {{total}}",
    nextBtnText: "Next",
    prevBtnText: "Back",
    doneBtnText: "Done",
    allowClose: true,
    popoverClass: "pg-tour",
    stagePadding: 6,
    stageRadius: 6,
    onDestroyed: () => {
      active = null
      ended?.()
    },
  })
  active.drive()
  return true
}

/** Closes the tour without reporting it as finished (the user left the page). */
export function stopTour(): void {
  ended = undefined
  active?.destroy()
}
