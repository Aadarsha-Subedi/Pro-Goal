import { PriorityLabel, StatusLabel, type TaskPriority, type TaskStatus } from "@/components/patterns/status"
import { ChatCircle, ListChecks, NotePencil } from "@/icons"

const TASKS: { key: string; title: string; status: TaskStatus; priority: TaskPriority; sub: string }[] = [
  { key: "PM-142", title: "Fix login redirect after email verification", status: "progress", priority: "urgent", sub: "2 of 3 subtasks" },
  { key: "PM-139", title: "Write the release checklist", status: "todo", priority: "high", sub: "0 of 4 subtasks" },
  { key: "PM-131", title: "Move uploads to the new bucket", status: "done", priority: "medium", sub: "3 of 3 subtasks" },
]

/** Figure 2: three tasks with status and priority, and the note and comments that sit on the first one. */
export function TasksNotesFigure() {
  return (
    <figure aria-labelledby="fig2">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Three tasks in the Apollo project with status, priority and subtask progress</caption>
        <thead>
          <tr className="border-y bp-rule-strong text-left">
            <th scope="col" className="bp-cell-label h-9 px-3 font-medium">Task</th>
            <th scope="col" className="bp-cell-label hidden h-9 px-3 font-medium sm:table-cell">Status</th>
            <th scope="col" className="bp-cell-label hidden h-9 px-3 font-medium md:table-cell">Priority</th>
            <th scope="col" className="bp-cell-label hidden h-9 px-3 font-medium md:table-cell">Subtasks</th>
          </tr>
        </thead>
        <tbody>
          {TASKS.map((t) => (
            <tr key={t.key} className="border-b bp-rule">
              <td className="px-3 py-2">
                <span className="bp-mono bp-muted">{t.key}</span> <span className="font-medium">{t.title}</span>
                <span className="mt-1 flex flex-wrap gap-x-4 sm:hidden"><StatusLabel status={t.status} /><PriorityLabel priority={t.priority} /></span>
              </td>
              <td className="hidden px-3 sm:table-cell"><StatusLabel status={t.status} /></td>
              <td className="hidden px-3 md:table-cell"><PriorityLabel priority={t.priority} /></td>
              <td className="bp-mono hidden px-3 text-xs bp-muted md:table-cell">{t.sub}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
        <div className="border bp-rule-strong p-3">
          <p className="flex items-center gap-2 font-medium"><NotePencil className="size-4" aria-hidden />Note on PM-142</p>
          <p className="mt-1 bp-muted">The redirect lost the return path when the link opened in a new tab. Keep it in the token, not the session.</p>
        </div>
        <div className="border bp-rule-strong p-3">
          <p className="flex items-center gap-2 font-medium"><ChatCircle className="size-4" aria-hidden />2 comments</p>
          <p className="mt-1 bp-muted"><span className="font-medium text-[var(--bp-ink)]">Sam:</span> Redirect fixed on staging. Can someone check Safari?</p>
        </div>
      </div>
      <figcaption id="fig2" className="bp-mono mt-2 flex items-center gap-2 text-xs bp-muted"><ListChecks className="size-3.5" aria-hidden />FIG. 2 — Tasks, subtasks, notes and comments in one project.</figcaption>
    </figure>
  )
}
