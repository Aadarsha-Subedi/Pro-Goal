import { Link } from "@tanstack/react-router"
import { Fragment, useState } from "react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { CaretDown, CaretRight, Check, Minus, WarningCircle } from "@/icons"
import type { Member, Registry } from "@/features/projects/api"
import { cellState, groupCounts, type GroupCount } from "./logic"
import { useAllGrants } from "./queries"

const CAP = 30

interface Column {
  member: Member
  codes: string[] | null
  state: "loading" | "error" | "ready"
}

function Cell({ count }: { count: GroupCount }) {
  const state = cellState(count)
  if (state === "all") return <span className="inline-flex items-center gap-1"><Check weight="bold" className="size-3.5" aria-hidden />All</span>
  if (state === "none") return <span className="inline-flex items-center gap-1 text-muted-foreground"><Minus className="size-3.5" aria-hidden />None</span>
  return <span className="inline-flex items-center gap-1 tabular-nums"><Minus weight="bold" className="size-3.5" aria-hidden />{count.held} of {count.total}</span>
}

/** Read-only "who can change what". Columns are members, rows are permission groups; open a group to see each permission. */
export function PermissionMatrix({ projectId, members, registry }: { projectId: string; members: Member[]; registry: Registry }) {
  const shown = members.slice(0, CAP)
  const fetched = shown.filter((m) => !m.is_owner)
  const results = useAllGrants(projectId, fetched.map((m) => m.id), true)
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const allCodes = registry.permissions.map((p) => p.code)

  const columns: Column[] = shown.map((member) => {
    if (member.is_owner) return { member, codes: allCodes, state: "ready" }
    const r = results[fetched.indexOf(member)]
    if (!r || r.isPending) return { member, codes: null, state: "loading" }
    if (r.isError || !r.data) return { member, codes: null, state: "error" }
    return { member, codes: r.data.permissions, state: "ready" }
  })
  const name = (m: Member) => m.display_name || m.first_name

  return (
    <div className="space-y-2">
      <div role="region" aria-label="Who can change what, scrolls sideways" tabIndex={0} className="rounded outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
      <Table aria-label="Who can change what">
        <TableHeader>
          <TableRow>
            <TableHead className="sticky left-0 bg-background">Area</TableHead>
            {columns.map(({ member }) => (
              <TableHead key={member.id} className="min-w-28">
                {member.is_owner ? <span>{name(member)} (owner)</span> : (
                  <Link to="/app/projects/$projectId/members/$userId/permissions" params={{ projectId, userId: member.id }} className="inline-flex items-center gap-1 rounded underline-offset-4 outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50">{name(member)}<CaretRight className="size-3" aria-hidden /></Link>
                )}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {registry.groups.map((group) => {
            const isOpen = !!open[group]
            const perCol = columns.map((c) => (c.codes ? groupCounts(c.codes, registry).find((x) => x.group === group)! : null))
            return (
              <Fragment key={group}>
                <TableRow>
                  <TableHead scope="row" className="sticky left-0 bg-background font-medium">
                    <Button variant="ghost" size="sm" className="-ml-2" icon={isOpen ? <CaretDown /> : <CaretRight />} aria-expanded={isOpen} aria-controls={`mx-${group}`} onClick={() => setOpen({ ...open, [group]: !isOpen })}>{group}</Button>
                  </TableHead>
                  {columns.map((c, i) => (
                    <TableCell key={c.member.id}>
                      {c.state === "loading" ? <Skeleton className="h-4 w-12" /> : c.state === "error" ? <span className="inline-flex items-center gap-1 text-muted-foreground"><WarningCircle className="size-3.5" aria-hidden />Unavailable</span> : <Cell count={perCol[i]!} />}
                    </TableCell>
                  ))}
                </TableRow>
                {isOpen && registry.permissions.filter((p) => p.group === group).map((p) => (
                  <TableRow key={p.code} id={`mx-${group}`}>
                    <TableHead scope="row" className="sticky left-0 bg-background pl-9 font-normal text-muted-foreground">{p.label}</TableHead>
                    {columns.map((c) => (
                      <TableCell key={c.member.id}>
                        {c.codes === null ? <span className="text-muted-foreground">{c.state === "loading" ? "…" : "Unavailable"}</span> : c.codes.includes(p.code)
                          ? <span className="inline-flex items-center gap-1"><Check weight="bold" className="size-3.5" aria-hidden />Yes</span>
                          : <span className="inline-flex items-center gap-1 text-muted-foreground"><Minus className="size-3.5" aria-hidden />No</span>}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </Fragment>
            )
          })}
        </TableBody>
      </Table>
      </div>
      {members.length > CAP && <p className="text-xs text-muted-foreground">Showing the first {CAP} of {members.length} members.</p>}
    </div>
  )
}
