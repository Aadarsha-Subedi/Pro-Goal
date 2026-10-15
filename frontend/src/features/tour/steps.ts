export interface TourStep {
  /** Matches `data-tour="…"` on the element to highlight. */
  target: string
  title: string
  description: string
  side?: "top" | "right" | "bottom" | "left"
}

/** In reading order. A step whose element is missing or hidden (a phone, another page) is skipped. */
export const TOUR_STEPS: TourStep[] = [
  { target: "nav-tasks", title: "Tasks", description: "The full list. Sort, filter and open any task to see its subtasks, notes and comments.", side: "right" },
  { target: "nav-board", title: "Board", description: "Tasks as columns by status. People with permission drag a card to change its status.", side: "right" },
  { target: "nav-notes", title: "Notes", description: "Project knowledge that is not a task. Every save keeps a revision.", side: "right" },
  { target: "nav-activity", title: "Activity", description: "Who changed what and when. You see your own actions here, and everyone's if you hold the permission.", side: "right" },
  { target: "nav-members", title: "Members", description: "Owners decide field by field what each person can change. A locked field tells you who to ask.", side: "right" },
  { target: "copy-project", title: "Make it yours", description: "This demo is shared and read-only. Copy it to your workspace to edit the tasks, notes and comments freely.", side: "bottom" },
  { target: "nav-explore", title: "Explore", description: "Find more demo projects, or projects whose owners are open to new members.", side: "right" },
  { target: "nav-projects", title: "Your projects", description: "Your own projects live here. Start one any time, or open a copy of a demo.", side: "right" },
]

type Finder = { querySelector: (selector: string) => Pick<Element, "getClientRects"> | null }

/** An element with no layout boxes is display:none (the desktop sidebar on a phone) or detached. */
export function visible(el: Pick<Element, "getClientRects"> | null): boolean {
  return !!el && el.getClientRects().length > 0
}

/** The steps whose targets are on screen right now. */
export function availableSteps(root: Finder = document): TourStep[] {
  return TOUR_STEPS.filter((s) => visible(root.querySelector(`[data-tour="${s.target}"]`)))
}
