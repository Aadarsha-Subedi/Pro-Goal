import { GoogleMark } from "@/components/patterns/google-mark"
import { useState } from "react"
import { toast } from "sonner"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { PriorityLabel, StatusLabel } from "@/components/patterns/status"
import { CalendarBlank, Check, Crown, Minus, Lock, PencilSimple, ShieldCheck, ShieldWarning, SlidersHorizontal, X } from "@/icons"
import { Section, Specimen } from "../section"

const ini = (n: string) => n.split(" ").map((p) => p[0]).join("")

/* ---------- permission model used by the editor and the member rows ---------- */

const GROUPS = [
  { name: "Tasks", grants: [["status", "Change status"], ["assignee", "Change assignee"], ["due", "Change due date"], ["priority", "Change priority"], ["delete", "Delete tasks"]] },
  { name: "Notes", grants: [["note-edit", "Edit notes"], ["note-delete", "Delete notes"]] },
  { name: "Members", grants: [["approve", "Approve join requests"], ["perms", "Change permissions"]] },
] as const

const ALL = GROUPS.flatMap((g) => g.grants.map(([id]) => id as string))
// What the person using the editor holds themselves (subset rule): they cannot hand out the rest.
const HELD = new Set(["status", "assignee", "due", "priority", "note-edit", "note-delete", "approve"])
const PRESETS: Record<string, string[]> = {
  viewer: [],
  member: ["status", "note-edit"],
  manager: ["status", "assignee", "due", "priority", "note-edit", "note-delete", "approve"],
}

const PRESET_NOTE: Record<string, string> = {
  viewer: "Viewer: can read everything, edit nothing.",
  member: "Member: changes task status and edits notes.",
  manager: "Manager: also assigns people, sets due date and priority, deletes notes and approves join requests.",
  custom: "Custom: a mix of permissions that matches no preset.",
}

function matchPreset(sel: Set<string>) {
  return Object.entries(PRESETS).find(([, v]) => v.length === sel.size && v.every((x) => sel.has(x)))?.[0] ?? "custom"
}

function PermissionEditor() {
  const [sel, setSel] = useState(new Set(PRESETS.member))
  const preset = matchPreset(sel)
  const toggle = (id: string, on: boolean) => {
    const next = new Set(sel)
    if (on) next.add(id)
    else next.delete(id)
    setSel(next)
  }
  return (
    <div className="rounded-lg border">
      <div className="flex flex-wrap items-center gap-3 border-b px-3 py-2.5">
        <ToggleGroup variant="outline" size="sm" value={[preset]} onValueChange={(v) => v[0] && v[0] !== "custom" && setSel(new Set(PRESETS[v[0]]))} aria-label="Preset">
          <ToggleGroupItem value="viewer">Viewer</ToggleGroupItem>
          <ToggleGroupItem value="member">Member</ToggleGroupItem>
          <ToggleGroupItem value="manager">Manager</ToggleGroupItem>
        </ToggleGroup>
        {preset === "custom" && <Badge variant="secondary">Custom</Badge>}
        <p className="ml-auto text-sm tabular-nums text-muted-foreground" aria-live="polite">Can edit {sel.size} of {ALL.length} permissions</p>
      </div>
      <p className="border-b px-3 py-2 text-xs text-muted-foreground">{PRESET_NOTE[preset]}</p>
      {GROUPS.map((g) => (
        <fieldset key={g.name} className="border-b last:border-b-0">
          <legend className="sr-only">{g.name}</legend>
          <p className="px-3 pt-2.5 text-xs font-medium text-muted-foreground" aria-hidden>{g.name}</p>
          <ul className="pb-1">
            {g.grants.map(([id, label]) => {
              const held = HELD.has(id)
              return (
                <li key={id} className="flex items-center gap-3 px-3 py-1.5 text-sm">
                  <Checkbox id={`g-${id}`} checked={sel.has(id)} disabled={!held} onCheckedChange={(v) => toggle(id, !!v)} aria-describedby={held ? undefined : `why-${id}`} />
                  <label htmlFor={`g-${id}`} className={held ? "" : "text-muted-foreground"}>{label}</label>
                  {!held && <span id={`why-${id}`} className="ml-auto inline-flex items-center gap-1 text-xs text-muted-foreground"><Lock className="size-3.5" /> You don't hold this permission</span>}
                </li>
              )
            })}
          </ul>
        </fieldset>
      ))}
    </div>
  )
}

/* ---------- members ---------- */

const MEMBERS = [
  { name: "Maya Chen", role: "Owner", owner: true, grants: ALL },
  { name: "Dev Patel", role: "Manager", grants: PRESETS.manager },
  { name: "Sam Rivera", role: "Member", grants: PRESETS.member },
  { name: "Ana Souza", role: "Viewer", grants: PRESETS.viewer },
]
const SHORT: Record<string, string> = { status: "Status", assignee: "Assignee", due: "Due date", priority: "Priority", delete: "Delete", "note-edit": "Edit notes", "note-delete": "Delete notes", approve: "Approve", perms: "Permissions" }

function MembersMatrix() {
  return (
    <div className="relative overflow-x-auto rounded-lg border">
      <table className="w-full min-w-[44rem] text-sm">
        <caption className="sr-only">Who can change what</caption>
        <thead>
          <tr className="border-b bg-surface text-left text-xs text-muted-foreground">
            <th scope="col" className="h-9 px-3 font-medium">Member</th>
            {ALL.map((g) => (
              <th key={g} scope="col" className="h-9 px-1 text-center font-medium whitespace-nowrap">{SHORT[g]}</th>
            ))}
            <th scope="col" className="w-10"><span className="sr-only">Edit</span></th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {MEMBERS.map((m) => (
            <tr key={m.name} className="h-(--row-h)">
              <th scope="row" className="px-3 text-left font-normal">
                <span className="flex items-center gap-2">
                  <Avatar size="sm"><AvatarFallback>{ini(m.name)}</AvatarFallback></Avatar>
                  <span className="min-w-0">
                    <span className="flex items-center gap-1.5 font-medium">{m.name}{m.owner && <Crown weight="fill" className="size-3.5 text-warning" aria-label="Owner" />}</span>
                    <span className="text-xs text-muted-foreground">{m.role}</span>
                  </span>
                </span>
              </th>
              {ALL.map((g) => {
                const on = m.grants.includes(g)
                return (
                  <td key={g} className="px-1 text-center">
                    {on ? <Check weight="bold" className="mx-auto size-4 text-success" aria-label="Can" /> : <Minus className="mx-auto size-4 text-muted-foreground/60" aria-label="Cannot" />}
                  </td>
                )
              })}
              <td className="px-1">
                <Button size="icon-sm" variant="ghost" label={`Edit permissions for ${m.name}`} disabled={m.owner}><SlidersHorizontal /></Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ---------- join requests ---------- */

const REQUESTS = [
  { id: "1", name: "Liam Novak", email: "liam@northwind.dev", time: "12 min ago" },
  { id: "2", name: "Priya Nair", email: "priya.nair@gmail.com", time: "Yesterday" },
]

function Requests() {
  const [rows, setRows] = useState(REQUESTS)
  const [roles, setRoles] = useState<Record<string, string>>({})
  const resolve = (r: (typeof REQUESTS)[number], verb: "Approved" | "Declined") => {
    const index = rows.findIndex((x) => x.id === r.id)
    setRows((cur) => cur.filter((x) => x.id !== r.id))
    const role = roles[r.id] ?? "member"
    toast(verb === "Approved" ? `Approved ${r.name} as ${role[0].toUpperCase() + role.slice(1)}` : `Declined ${r.name}`, {
      duration: 9000,
      action: { label: "Undo", onClick: () => setRows((cur) => { const next = [...cur]; next.splice(Math.min(index, next.length), 0, r); return next }) },
    })
  }
  return (
    <div className="rounded-lg border">
      <div className="flex h-10 items-center gap-2 border-b bg-surface px-3 text-sm">
        <span className="font-medium">{rows.length} pending</span>
        <span className="text-xs text-muted-foreground">Joined with code <span className="font-mono">K7P2QX</span></span>
      </div>
      {rows.length === 0 ? (
        <p className="px-4 py-6 text-center text-sm text-muted-foreground">No pending requests. Share your join code to invite people.</p>
      ) : (
        <ul className="divide-y">
          {rows.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 py-2.5">
              <Avatar size="sm"><AvatarFallback>{ini(r.name)}</AvatarFallback></Avatar>
              <div className="min-w-0 flex-1 basis-44 text-sm">
                <p className="font-medium">{r.name}</p>
                <p className="truncate text-sm text-muted-foreground">{r.email}</p>
                <p className="text-xs text-muted-foreground">{r.time}</p>
              </div>
              <Select
                value={roles[r.id] ?? "member"}
                onValueChange={(v) => v && setRoles({ ...roles, [r.id]: v })}
                items={[{ value: "viewer", label: "Viewer" }, { value: "member", label: "Member" }, { value: "manager", label: "Manager" }, { value: "admin", label: "Admin" }]}
              >
                <SelectTrigger size="sm" aria-label={`Role for ${r.name}`} className="w-28"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="viewer">Viewer</SelectItem>
                  <SelectItem value="member">Member</SelectItem>
                  <SelectItem value="manager">Manager</SelectItem>
                  <SelectItem value="admin" disabled>Admin <Lock className="size-3.5" aria-label="Locked" /></SelectItem>
                </SelectContent>
              </Select>
              <Button size="sm" variant="ghost" icon={<X />} onClick={() => resolve(r, "Declined")}>Decline</Button>
              <Button size="sm" variant="outline" icon={<Check weight="bold" />} onClick={() => resolve(r, "Approved")}>Approve</Button>
            </li>
          ))}
        </ul>
      )}
      <p className="border-t px-3 py-2 text-xs text-muted-foreground">A lock means the role includes permissions you don't hold. You can grant only what you hold.</p>
    </div>
  )
}

/* ---------- permissions on the task row (the signature) ---------- */

const ROWS = [
  { n: 142, title: "Fix login redirect after email verification", status: "progress", priority: "urgent", due: "Oct 12" },
  { n: 141, title: "Add rate limit headers to public endpoints", status: "todo", priority: "high", due: "Oct 14" },
  { n: 139, title: "Kanban: sort columns by due date", status: "todo", priority: "medium", due: "Oct 15" },
] as const

/** Tap, click or press Enter to see why a field is locked. Works on touch and keyboard, not only hover. */
function Locked({ children, reason }: { children: React.ReactNode; reason: string }) {
  return (
    <Popover>
      <PopoverTrigger
        render={<button type="button" className="inline-flex min-h-6 cursor-not-allowed items-center gap-1.5 rounded text-muted-foreground" aria-label={`Locked. ${reason}`} />}
      >
        {children}
        <Lock className="size-3.5" aria-hidden />
      </PopoverTrigger>
      <PopoverContent className="w-60 text-sm">{reason}</PopoverContent>
    </Popover>
  )
}

function TaskRowPermissions() {
  return (
    <div className="overflow-hidden rounded-lg border">
      <div className="flex min-h-10 flex-wrap items-center gap-2 border-b bg-surface px-3 py-1.5 text-sm">
        <span className="font-medium">Viewing as Sam Rivera</span>
        <Badge variant="secondary">Member</Badge>
        <span className="ml-auto text-xs tabular-nums text-muted-foreground">Can edit 2 of 9 permissions</span>
      </div>
      <ul className="divide-y">
        {ROWS.map((t) => (
          <li key={t.n} className="group flex flex-col gap-1 px-3 py-2 text-sm md:grid md:h-(--row-h) md:grid-cols-[4.5rem_1fr_9rem_8rem_6rem] md:items-center md:gap-3 md:py-0">
            <span className="flex items-baseline gap-3 md:contents">
              <span className="font-mono text-xs whitespace-nowrap text-muted-foreground">PM-{t.n}</span>
              <span className="truncate font-medium">{t.title}</span>
            </span>
            <span className="flex flex-wrap items-center gap-x-4 gap-y-1 md:contents">
              <Button variant="ghost" size="sm" className="justify-start" iconEnd={<PencilSimple className="opacity-0 transition-opacity group-focus-within:opacity-60 group-hover:opacity-60" />}><StatusLabel status={t.status} /></Button>
              <Locked reason="Only managers can change priority. Ask Maya Chen, the owner."><PriorityLabel priority={t.priority} /></Locked>
              <Locked reason="Only members with the due date permission can change this. Ask Maya Chen, the owner."><span className="inline-flex items-center gap-1.5 tabular-nums"><CalendarBlank className="size-3.5" />{t.due}</span></Locked>
            </span>
          </li>
        ))}
      </ul>
      <p className="border-t px-3 py-2 text-xs text-muted-foreground">A lock means you can read but not edit. Tap it to see why.</p>
    </div>
  )
}

/* ---------- section ---------- */

export function Access() {
  return (
    <Section id="access" title="Permissions and access" intro="Reading is open to every member; permissions only unlock writes. The interface shows what you can and cannot change before you try.">
      <Specimen title="On the task row" note="Editable cells show a pencil on hover or focus; locked cells show a lock, and tapping one shows the reason">
        <TaskRowPermissions />
      </Specimen>

      <div className="grid gap-12 lg:grid-cols-2">
        <Specimen title="Locked field" note="Read-only with the reason on hover or focus">
          <Field>
            <FieldLabel htmlFor="due-ro" className="gap-1.5">Due date <Lock className="size-3.5 text-muted-foreground" aria-hidden /></FieldLabel>
            <Tooltip>
              <TooltipTrigger render={<div className="w-full" />}>
                <Input id="due-ro" readOnly value="Oct 14, 2026" aria-describedby="due-why" className="cursor-not-allowed bg-muted/50 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>Only members with the due date permission can change this.</TooltipContent>
            </Tooltip>
            <FieldDescription id="due-why">You can read this field but not edit it. Ask the owner for access.</FieldDescription>
          </Field>
        </Specimen>

        <Specimen title="Join requests" note="Owner inbox. Each person is reviewed and given a role.">
          <Requests />
        </Specimen>
      </div>

      <Specimen title="Members" note="Who can change what, at a glance">
        <MembersMatrix />
      </Specimen>

      <div className="grid gap-12 lg:grid-cols-2">
        <Specimen title="Permission editor" note="Presets set the grants, edits switch to Custom. You can grant only what you hold.">
          <PermissionEditor />
        </Specimen>

        <Specimen title="Confirm it's you" note="Required for sensitive owner actions; shows who is affected">
          <Dialog>
            <DialogTrigger render={<Button variant="destructive" icon={<ShieldWarning />}>Transfer ownership…</Button>} />
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Transfer ownership</DialogTitle>
                <DialogDescription>You become a Manager. Only the new owner can transfer it back.</DialogDescription>
              </DialogHeader>
              <div className="flex items-center gap-3 rounded-md bg-muted px-3 py-2.5 text-sm">
                <Avatar size="sm"><AvatarFallback>DP</AvatarFallback></Avatar>
                <div><p className="font-medium">Dev Patel</p><p className="text-xs text-muted-foreground">New owner of Apollo</p></div>
              </div>
              <Field>
                <FieldLabel htmlFor="reauth">Confirm with your password</FieldLabel>
                <Input id="reauth" type="password" autoComplete="current-password" />
                <Button variant="ghost" size="sm" className="mt-1 justify-start self-start" icon={<GoogleMark />}>Use Google instead</Button>
              </Field>
              <DialogFooter>
                <DialogClose render={<Button variant="outline">Cancel</Button>} />
                <Button variant="solid-destructive" icon={<ShieldCheck />}>Confirm and transfer</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </Specimen>
      </div>
    </Section>
  )
}
