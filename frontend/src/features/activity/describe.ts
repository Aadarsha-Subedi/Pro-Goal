import type { PhosphorIcon } from "@/icons"
import {
  Archive, ArrowCounterClockwise, ChatCircle, ClockCounterClockwise, Crown, FolderSimple, Key, NotePencil, Paperclip, PencilSimple, Plus, PlugsConnected, ShieldCheck, SignOut, Tag, Trash, UserMinus, UserPlus,
} from "@/icons"
import type { ActivityEntry } from "./api"

export interface Detail {
  field: string
  from?: string
  to?: string
  note?: string
}

export interface Described {
  /** What the person did, to follow their name: "created PMS-4 Audit probe". */
  verb: string
  icon: PhosphorIcon
  details: Detail[]
  /** Where to open the thing, when the entry names it. */
  link?: { kind: "task"; number: number } | { kind: "note"; id: string }
}

type Changes = Record<string, unknown>

const LABELS: Record<string, string> = { task_key: "Task key", start_date: "Start date", end_date: "End date", due_date: "Due date", is_listed: "Listed on Explore", parent: "Parent task" }
const humanize = (key: string) => LABELS[key] ?? key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ")

function show(value: unknown): string {
  if (value === null || value === undefined || value === "") return "none"
  if (Array.isArray(value)) return value.length ? value.map(show).join(", ") : "none"
  if (typeof value === "boolean") return value ? "yes" : "no"
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v)

/** `{field: {from, to}}` pairs and `{field: {changed: true}}` markers, as the backend writes them. */
export function fieldDetails(changes: Changes): Detail[] {
  const out: Detail[] = []
  // Permission changes and Slack channel events are written as plain lists at the top level.
  if (Array.isArray(changes.added) && changes.added.length) out.push({ field: "Added", note: show(changes.added) })
  if (Array.isArray(changes.removed) && changes.removed.length) out.push({ field: "Removed", note: show(changes.removed) })
  if (Array.isArray(changes.events) && changes.events.length) out.push({ field: "Events", note: show(changes.events) })
  for (const [key, value] of Object.entries(changes)) {
    if (!isRecord(value)) continue
    if ("from" in value || "to" in value) out.push({ field: humanize(key), from: show(value.from), to: show(value.to) })
    else if (value.changed === true) out.push({ field: humanize(key), note: "changed" })
    else if ("added" in value || "removed" in value) out.push({ field: humanize(key), note: [Array.isArray(value.added) && value.added.length ? `added ${show(value.added)}` : "", Array.isArray(value.removed) && value.removed.length ? `removed ${show(value.removed)}` : ""].filter(Boolean).join(", ") })
  }
  return out
}

const num = (v: unknown) => (typeof v === "number" ? v : undefined)
const str = (v: unknown) => (typeof v === "string" ? v : undefined)

type Rule = (e: ActivityEntry, c: Changes, key: string) => Omit<Described, "details"> & { details?: Detail[] }

const RULES: Record<string, Rule> = {
  "project.created": (_e, c) => ({ verb: `created the project${str(c.name) ? ` ${str(c.name)}` : ""}`, icon: FolderSimple }),
  "project.updated": () => ({ verb: "updated the project", icon: PencilSimple }),
  "project.archived": () => ({ verb: "archived the project", icon: Archive }),
  "project.unarchived": () => ({ verb: "unarchived the project", icon: ArrowCounterClockwise }),
  "project.deleted": () => ({ verb: "scheduled the project for deletion", icon: Trash }),
  "project.restored": () => ({ verb: "restored the project", icon: ArrowCounterClockwise }),
  "project.join_code_regenerated": () => ({ verb: "made a new join code", icon: Key }),
  "join_request.created": () => ({ verb: "asked to join", icon: UserPlus }),
  "join_request.approved": () => ({ verb: "approved a join request", icon: UserPlus }),
  "join_request.rejected": () => ({ verb: "declined a join request", icon: UserMinus }),
  "member.removed": () => ({ verb: "removed a member", icon: UserMinus }),
  "member.joined": () => ({ verb: "joined the project", icon: UserPlus }),
  "member.left": () => ({ verb: "left the project", icon: SignOut }),
  "member.permissions_changed": () => ({ verb: "changed a member's permissions", icon: ShieldCheck }),
  "ownership.transfer_started": () => ({ verb: "offered to transfer ownership", icon: Crown }),
  "ownership.transfer_cancelled": () => ({ verb: "cancelled the ownership offer", icon: Crown }),
  "ownership.transferred": () => ({ verb: "became the owner", icon: Crown }),
  "task.created": (_e, c, key) => ({ verb: `created ${taskLabel(key, c)}${str(c.title) ? ` ${str(c.title)}` : ""}`, icon: Plus, link: taskLink(c) }),
  "task.updated": () => ({ verb: "updated a task", icon: PencilSimple }),
  "task.deleted": (_e, c, key) => ({ verb: `deleted ${taskLabel(key, c)}${num(c.subtasks) ? ` and ${num(c.subtasks)} ${num(c.subtasks) === 1 ? "subtask" : "subtasks"}` : ""}`, icon: Trash }),
  "task.restored": (_e, c, key) => ({ verb: `restored ${taskLabel(key, c)}`, icon: ArrowCounterClockwise, link: taskLink(c) }),
  "note.created": (_e, c) => ({ verb: `created the note ${str(c.title) ?? ""}`.trim(), icon: NotePencil }),
  "note.updated": () => ({ verb: "edited a note", icon: NotePencil }),
  "note.deleted": (_e, c) => ({ verb: `deleted the note ${str(c.title) ?? ""}`.trim(), icon: Trash }),
  "note.linked": () => ({ verb: "linked a note to a task", icon: NotePencil }),
  "note.unlinked": () => ({ verb: "unlinked a note from a task", icon: NotePencil }),
  "comment.created": (_e, c, key) => ({ verb: `commented on ${num(c.task) ? `${key}-${num(c.task)}` : "a task"}`, icon: ChatCircle, link: num(c.task) ? { kind: "task", number: num(c.task)! } : undefined }),
  "comment.edited": (_e, c, key) => ({ verb: `edited a comment on ${num(c.task) ? `${key}-${num(c.task)}` : "a task"}`, icon: ChatCircle, link: num(c.task) ? { kind: "task", number: num(c.task)! } : undefined }),
  "comment.deleted": (_e, c, key) => ({ verb: `deleted a comment on ${num(c.task) ? `${key}-${num(c.task)}` : "a task"}`, icon: Trash }),
  "status.created": (_e, c) => ({ verb: `added the status ${str(c.name) ?? ""}`.trim(), icon: Tag }),
  "status.updated": () => ({ verb: "changed a status", icon: Tag }),
  "status.deleted": (_e, c) => ({ verb: `removed the status ${str(c.name) ?? ""}`.trim(), icon: Trash }),
  "priority.created": (_e, c) => ({ verb: `added the priority ${str(c.name) ?? ""}`.trim(), icon: Tag }),
  "priority.updated": () => ({ verb: "changed a priority", icon: Tag }),
  "priority.deleted": (_e, c) => ({ verb: `removed the priority ${str(c.name) ?? ""}`.trim(), icon: Trash }),
  "attachment.added": (_e, c) => ({ verb: `attached ${str(c.filename) ?? str(c.name) ?? "a file"}`, icon: Paperclip }),
  "attachment.deleted": (_e, c) => ({ verb: `removed ${str(c.filename) ?? str(c.name) ?? "a file"}`, icon: Trash }),
  "integration.connected": () => ({ verb: "connected an integration", icon: PlugsConnected }),
  "integration.disconnected": () => ({ verb: "disconnected an integration", icon: PlugsConnected }),
  "integration.delivery_replayed": () => ({ verb: "sent a failed delivery again", icon: PlugsConnected }),
  "integration.slack_mapping_saved": (_e, c) => ({ verb: `saved the Slack channel ${str(c.channel) ? `#${str(c.channel)}` : ""}`.trim(), icon: PlugsConnected }),
  "integration.slack_mapping_removed": (_e, c) => ({ verb: `removed the Slack channel ${str(c.channel) ? `#${str(c.channel)}` : ""}`.trim(), icon: PlugsConnected }),
}

const taskLabel = (key: string, c: Changes) => (num(c.number) ? `${key}-${num(c.number)}` : "a task")
const taskLink = (c: Changes): Described["link"] => (num(c.number) ? { kind: "task", number: num(c.number)! } : undefined)

export const KNOWN_ACTIONS = Object.keys(RULES)

/** One feed entry as a sentence fragment, an icon, field changes and a link. Unknown actions still read as words. */
export function describe(entry: ActivityEntry, taskKey: string): Described {
  const rule = RULES[entry.action]
  if (!rule) return { verb: entry.action.replace(/[._]/g, " "), icon: ClockCounterClockwise, details: fieldDetails(entry.changes) }
  const base = rule(entry, entry.changes, taskKey)
  const link = base.link ?? (entry.entity_type === "note" && entry.entity_id && !entry.action.endsWith("deleted") ? { kind: "note" as const, id: entry.entity_id } : undefined)
  return { ...base, link, details: base.details ?? fieldDetails(entry.changes) }
}

export const ENTITY_OPTIONS = [
  { value: "task", label: "Tasks" },
  { value: "comment", label: "Comments" },
  { value: "note", label: "Notes" },
  { value: "attachment", label: "Files" },
  { value: "status", label: "Statuses" },
  { value: "priority", label: "Priorities" },
  { value: "member", label: "Members" },
  { value: "join_request", label: "Join requests" },
  { value: "ownership_transfer", label: "Ownership" },
  { value: "project", label: "Project" },
  { value: "integration", label: "Integrations" },
]
