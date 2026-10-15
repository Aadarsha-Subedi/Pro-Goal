import type { PhosphorIcon } from "@/icons"
import { Bell, ChatCircle, Flag, FolderSimple, UserPlus, UserMinus, UserCirclePlus, ListChecks, PencilSimple, Clock, Plus, WarningCircle } from "@/icons"

export interface EventInfo {
  label: string
  icon: PhosphorIcon
}

export const EVENT_INFO: Record<string, EventInfo> = {
  task_created: { label: "Task created", icon: Plus },
  task_updated: { label: "Task changed", icon: PencilSimple },
  task_assigned: { label: "Task assigned", icon: UserCirclePlus },
  task_due_soon: { label: "Task due soon", icon: Clock },
  task_overdue: { label: "Task overdue", icon: WarningCircle },
  comment_added: { label: "New comment", icon: ChatCircle },
  member_joined: { label: "Member joined", icon: UserPlus },
  member_removed: { label: "Member removed", icon: UserMinus },
  join_request_created: { label: "New join request", icon: Flag },
  project_archived: { label: "Project archived", icon: FolderSimple },
}

export const eventInfo = (type: string): EventInfo => EVENT_INFO[type] ?? { label: type.replace(/_/g, " "), icon: Bell }

/** The catalog grouped the way people think about it, for the mapping dialog. */
export const EVENT_GROUPS: { name: string; icon: PhosphorIcon; events: string[] }[] = [
  { name: "Tasks", icon: ListChecks, events: ["task_created", "task_updated", "task_assigned", "task_due_soon", "task_overdue"] },
  { name: "Comments", icon: ChatCircle, events: ["comment_added"] },
  { name: "Members", icon: UserPlus, events: ["member_joined", "member_removed", "join_request_created"] },
  { name: "Project", icon: FolderSimple, events: ["project_archived"] },
]

export const ALL_EVENTS = EVENT_GROUPS.flatMap((g) => g.events)

/** "All 10 events" or "3 events: Task created, Task assigned, New comment". */
export function summarizeEvents(enabled: readonly string[]): string {
  if (enabled.length === 0) return "No events"
  if (enabled.length === ALL_EVENTS.length) return `All ${ALL_EVENTS.length} events`
  const names = enabled.map((e) => eventInfo(e).label)
  return `${enabled.length} ${enabled.length === 1 ? "event" : "events"}: ${names.slice(0, 3).join(", ")}${names.length > 3 ? ` and ${names.length - 3} more` : ""}`
}

export function toggleEvent(enabled: readonly string[], event: string, on: boolean): string[] {
  const rest = enabled.filter((e) => e !== event)
  return on ? ALL_EVENTS.filter((e) => e === event || rest.includes(e)) : rest
}
