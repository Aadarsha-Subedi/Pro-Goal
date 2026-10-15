import { createSortedRowModel, flexRender, columnVisibilityFeature, rowSelectionFeature, rowSortingFeature, sortFns, tableFeatures, useTable, type ColumnDef } from "@tanstack/react-table"
import { useMemo } from "react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { PriorityLabel, StatusLabel } from "@/components/patterns/status"
import { ArrowDown, ArrowUp, CaretUpDown, Copy, DotsThree, PencilSimple, Trash, UserSwitch } from "@/icons"
import { TASKS, type Task } from "../data"
import { Section, Specimen } from "../section"

const features = tableFeatures({ rowSortingFeature, rowSelectionFeature, columnVisibilityFeature, sortedRowModel: createSortedRowModel(), sortFns })

const HIDE_NARROW = new Set(["priority", "assignee"])

function SortHeader({ label, column }: { label: string; column: { getIsSorted: () => false | "asc" | "desc"; toggleSorting: (d?: boolean) => void } }) {
  const s = column.getIsSorted()
  return (
    <Button variant="ghost" size="xs" className="-ml-2 text-muted-foreground" iconEnd={s === "asc" ? <ArrowUp /> : s === "desc" ? <ArrowDown /> : <CaretUpDown />} onClick={() => column.toggleSorting(s === "asc")}>
      {label}
    </Button>
  )
}

export function DataTableSection() {
  const columns = useMemo<ColumnDef<typeof features, Task>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <Checkbox aria-label="Select all" checked={table.getIsAllRowsSelected()} onCheckedChange={(v) => table.toggleAllRowsSelected(!!v)} />
        ),
        cell: ({ row }) => <Checkbox aria-label="Select row" checked={row.getIsSelected()} onCheckedChange={(v) => row.toggleSelected(!!v)} />,
      },
      { accessorKey: "number", header: ({ column }) => <SortHeader label="ID" column={column} />, cell: ({ row }) => <span className="font-mono text-xs text-muted-foreground">PM-{row.original.number}</span> },
      { accessorKey: "title", header: ({ column }) => <SortHeader label="Title" column={column} />, cell: ({ row }) => (
        <div className="flex items-center gap-2"><span className="truncate font-medium">{row.original.title}</span>{row.original.tags.map((t) => <Badge key={t} variant="secondary">{t}</Badge>)}</div>
      ) },
      { accessorKey: "status", header: ({ column }) => <SortHeader label="Status" column={column} />, cell: ({ row }) => <StatusLabel status={row.original.status} /> },
      { accessorKey: "priority", header: "Priority", cell: ({ row }) => <PriorityLabel priority={row.original.priority} /> },
      { accessorKey: "assignee", header: "Assignee", cell: ({ row }) => (
        <span className="inline-flex items-center gap-2"><Avatar size="sm"><AvatarFallback>{row.original.assignee.split(" ").map((p) => p[0]).join("")}</AvatarFallback></Avatar>{row.original.assignee}</span>
      ) },
      { accessorKey: "due", header: "Due", cell: ({ row }) => <span className="tabular-nums text-muted-foreground">{row.original.due}</span> },
      {
        id: "actions",
        header: () => <span className="sr-only">Actions</span>,
        cell: () => (
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" label="Row actions"><DotsThree weight="bold" /></Button>} />
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuItem><PencilSimple /> Edit</DropdownMenuItem>
              <DropdownMenuItem><Copy /> Duplicate</DropdownMenuItem>
              <DropdownMenuItem><UserSwitch /> Reassign</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive"><Trash /> Delete</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ),
      },
    ],
    [],
  )

  const table = useTable<typeof features, Task>({
    features,
    columns,
    data: TASKS,
    getRowId: (r) => r.id,
  })
  const selected = table.getSelectedRowModel().rows.length

  return (
    <Section id="data" title="Data table" intro="TanStack Table. Sticky header, sortable columns, selection with a bulk bar, row actions. Status and priority are icon plus text, never filled chips.">
      <Specimen title="Task list" note="Click headers to sort, tick rows to select">
        <div className="overflow-hidden rounded-lg border">
          <div className="flex h-10 items-center gap-2 border-b bg-surface px-3 text-sm" aria-live="polite">
            {selected ? (
              <>
                <span className="font-medium">{selected} selected</span>
                <Button size="xs" variant="outline" icon={<UserSwitch />}>Reassign</Button>
                <Button size="xs" variant="destructive" icon={<Trash />}>Delete</Button>
              </>
            ) : (
              <span className="text-muted-foreground">{TASKS.length} tasks</span>
            )}
          </div>
          <Table>
            <caption className="sr-only">Tasks, sortable by column</caption>
            <TableHeader>
              {table.getHeaderGroups().map((hg) => (
                <TableRow key={hg.id} className="hover:bg-transparent">
                  {hg.headers.map((h) => (
                    <TableHead key={h.id} className={`h-9 ${HIDE_NARROW.has(h.column.id) ? "hidden xl:table-cell" : ""}`}>{h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}</TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} data-state={row.getIsSelected() ? "selected" : undefined} className="h-(--row-h)">
                  {row.getVisibleCells().map((c) => (
                    <TableCell key={c.id} className={`py-0 ${HIDE_NARROW.has(c.column.id) ? "hidden xl:table-cell" : ""}`}>{flexRender(c.column.columnDef.cell, c.getContext())}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Specimen>
    </Section>
  )
}
