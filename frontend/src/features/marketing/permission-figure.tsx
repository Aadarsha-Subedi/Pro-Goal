import { Check, Minus } from "@/icons"
import { Dimension } from "./dimension"

const MEMBERS = [
  { name: "Maya", role: "Owner" },
  { name: "Dev", role: "Manager" },
  { name: "Sam", role: "Member" },
  { name: "Ana", role: "Viewer" },
]
const PERMS = [
  { label: "Change status", can: [1, 1, 1, 0] },
  { label: "Change assignee", can: [1, 1, 0, 0] },
  { label: "Change due date", can: [1, 1, 0, 0] },
  { label: "Change priority", can: [1, 1, 0, 0] },
  { label: "Delete tasks", can: [1, 0, 0, 0] },
  { label: "Edit notes", can: [1, 1, 1, 0] },
  { label: "Delete notes", can: [1, 1, 0, 0] },
  { label: "Approve join requests", can: [1, 1, 0, 0] },
  { label: "Change permissions", can: [1, 0, 0, 0] },
]
const COUNTS = MEMBERS.map((_, i) => PERMS.filter((p) => p.can[i]).length)

/** Figure 1: who can change what in a project, one column per member, with a dimension under each. */
export function PermissionFigure() {
  return (
    <figure aria-labelledby="fig4">
      <table className="w-full table-fixed border-collapse text-sm">
        <caption className="sr-only">Who can change what in the Apollo project</caption>
        <thead>
          <tr aria-hidden>
            <td className="w-[38%] sm:w-[34%]" />
            <td colSpan={MEMBERS.length} className="px-1 pb-2"><Dimension>4 members</Dimension></td>
          </tr>
          <tr className="border-b bp-rule-strong text-left">
            <th scope="col" className="bp-cell-label h-9 w-[38%] pr-2 font-medium sm:w-[34%]">Permission</th>
            {MEMBERS.map((m) => (
              <th key={m.name} scope="col" className="h-10 px-1 text-center font-medium">
                <span className="block text-sm">{m.name}</span>
                <span className="bp-role block">{m.role}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {PERMS.map((p) => (
            <tr key={p.label} className="border-b bp-rule">
              <th scope="row" className="h-8 pr-2 text-left font-normal lg:h-8">{p.label}</th>
              {p.can.map((c, i) => (
                <td key={MEMBERS[i].name} className="px-1 text-center">
                  {c ? <Check weight="bold" className="mx-auto size-4 text-success" aria-label="Can change" /> : <Minus className="mx-auto size-4 bp-muted" aria-label="Cannot change" />}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row" className="bp-cell-label pt-3 pr-2 text-left font-medium">Can change, of 9</th>
            {COUNTS.map((n, i) => (
              <td key={MEMBERS[i].name} className="px-1 pt-2 sm:px-2"><Dimension>{n}<span className="hidden sm:inline"> of 9</span></Dimension></td>
            ))}
          </tr>
        </tfoot>
      </table>
      <figcaption id="fig4" className="bp-mono mt-2 text-xs bp-muted">FIG. 4 — Who can change what in a project. The owner edits these.</figcaption>
    </figure>
  )
}
