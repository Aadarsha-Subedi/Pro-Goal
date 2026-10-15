import type { ExploreProject } from "./api"

export type Action =
  | { kind: "pending" }
  | { kind: "cooldown"; until: string }
  | { kind: "request" }
  | { kind: "join" }

/** What the row offers: join at once (demo projects), waiting for the owner, locked for a day after a decline, or a request. The backend never lists projects you are already in. */
export function actionFor(project: ExploreProject, now: number = Date.now()): Action {
  if (project.is_demo) return { kind: "join" }
  const r = project.my_request
  if (r.state === "pending") return { kind: "pending" }
  if (r.state === "cooldown" && r.cooldown_until && Date.parse(r.cooldown_until) > now) return { kind: "cooldown", until: r.cooldown_until }
  return { kind: "request" }
}
