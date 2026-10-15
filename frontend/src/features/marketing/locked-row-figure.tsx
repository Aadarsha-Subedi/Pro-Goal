import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { PriorityLabel, StatusLabel } from "@/components/patterns/status"
import { CalendarBlank, Lock, PencilSimple } from "@/icons"

function Locked({ children, reason }: { children: React.ReactNode; reason: string }) {
  return (
    <Popover>
      <PopoverTrigger render={<button type="button" className="inline-flex min-h-6 pointer-coarse:min-h-11 cursor-not-allowed items-center gap-1.5 bp-muted" aria-label={`Locked. ${reason}`} />}>
        {children}
        <Lock className="size-3.5" aria-hidden />
      </PopoverTrigger>
      <PopoverContent className="w-60 text-sm">{reason}</PopoverContent>
    </Popover>
  )
}

/** Detail A: a task row as Sam sees it. Editable cells show a pencil, locked cells explain themselves. */
export function LockedRowFigure() {
  return (
    <figure aria-labelledby="detA">
      <div className="border-y bp-rule-strong py-3">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
          <span className="bp-mono bp-muted">PM-142</span>
          <span className="min-w-0 flex-1 basis-56 font-medium">Fix login redirect after email verification</span>
          <span className="inline-flex items-center gap-1.5"><StatusLabel status="progress" /><PencilSimple className="size-3.5 opacity-60" aria-label="You can edit this" /></span>
          <Locked reason="Only managers can change priority. Ask Maya Chen, the owner."><PriorityLabel priority="urgent" /></Locked>
          <Locked reason="Only members with the due date permission can change this. Ask Maya Chen, the owner."><span className="inline-flex items-center gap-1.5 tabular-nums"><CalendarBlank className="size-3.5" />Oct 12</span></Locked>
        </div>
      </div>
      <ul className="mt-3 space-y-1 text-sm bp-muted">
        <li className="flex items-center gap-2"><Lock className="size-3.5 shrink-0" aria-hidden />Priority is locked. Only managers can change it. Ask Maya Chen, the owner.</li>
        <li className="flex items-center gap-2"><Lock className="size-3.5 shrink-0" aria-hidden />Due date is locked. It needs the due date permission. Ask Maya Chen, the owner.</li>
      </ul>
      <figcaption id="detA" className="bp-mono mt-2 text-xs bp-muted">DETAIL A — A task row as Sam sees it: a lock where they can't edit, and who to ask.</figcaption>
    </figure>
  )
}
