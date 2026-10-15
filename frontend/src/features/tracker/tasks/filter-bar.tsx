import { DatePicker } from "@/components/patterns/date-picker"
import { FilterSelect } from "@/components/patterns/filter-select"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { FunnelSimple, X } from "@/icons"
import { activeFilterCount, SORTS, withSearch, type TaskSearch } from "../search"
import type { Priority, Status } from "../api"
import type { Person } from "@/components/patterns/member-picker"
import type { LazyOptions } from "@/lib/lazy-options"
import { SearchBox } from "@/components/patterns/search-box"

interface FilterBarProps {
  search: TaskSearch
  onChange: (next: TaskSearch) => void
  statuses: LazyOptions<Status>
  priorities: LazyOptions<Priority>
  people: LazyOptions<Person>
  /** The board keeps its own sort and has no paging, so it hides the sort and subtask controls. */
  hideSort?: boolean
}

/** Search, the three everyday filters, and a "More" popover for the rest. State lives in the URL through `onChange`. */
export function FilterBar({ search, onChange, statuses, priorities, people, hideSort }: FilterBarProps) {
  const set = (patch: Partial<TaskSearch>) => onChange(withSearch(search, patch))
  const moreCount = [search.tag, search.after, search.before, search.overdue, search.subtasks].filter(Boolean).length
  const total = activeFilterCount(search)

  return (
    <div role="search" aria-label="Filter tasks" className="flex flex-wrap items-center gap-2">
      <SearchBox value={search.q ?? ""} onCommit={(q) => set({ q })} placeholder="Search titles" />
      <FilterSelect label="Status" value={search.status} onChange={(v) => set({ status: v })} source={statuses} options={statuses.items.map((s) => ({ value: s.id, label: s.name }))} />
      <FilterSelect label="Priority" value={search.priority} onChange={(v) => set({ priority: v })} source={priorities} options={priorities.items.map((p) => ({ value: p.id, label: p.name }))} />
      <FilterSelect label="Assignee" value={search.assignee} onChange={(v) => set({ assignee: v })} source={people} options={people.items.map((p) => ({ value: p.id, label: p.name }))} />
      <Popover>
        <PopoverTrigger render={<Button variant="outline" icon={<FunnelSimple />}>More{moreCount > 0 && <Badge variant="secondary" className="ml-1">{moreCount}</Badge>}</Button>} />
        <PopoverContent align="start" className="w-72 gap-3">
          <Field>
            <FieldLabel htmlFor="f-tag">Tag</FieldLabel>
            <Input id="f-tag" value={search.tag ?? ""} maxLength={30} onChange={(e) => set({ tag: e.target.value.trim().toLowerCase() || undefined })} placeholder="bug" />
          </Field>
          <Field>
            <FieldLabel htmlFor="f-after">Due on or after</FieldLabel>
            <DatePicker id="f-after" placeholder="Any date" value={search.after ?? null} onChange={(v) => set({ after: v ?? undefined })} />
          </Field>
          <Field>
            <FieldLabel htmlFor="f-before">Due on or before</FieldLabel>
            <DatePicker id="f-before" placeholder="Any date" value={search.before ?? null} onChange={(v) => set({ before: v ?? undefined })} />
          </Field>
          <Field orientation="horizontal">
            <Switch id="f-overdue" checked={!!search.overdue} onCheckedChange={(v) => set({ overdue: v || undefined })} />
            <FieldLabel htmlFor="f-overdue">Overdue only</FieldLabel>
          </Field>
          {!hideSort && (
            <Field orientation="horizontal">
              <Switch id="f-sub" checked={!!search.subtasks} onCheckedChange={(v) => set({ subtasks: v || undefined })} />
              <FieldLabel htmlFor="f-sub">Include subtasks</FieldLabel>
            </Field>
          )}
        </PopoverContent>
      </Popover>
      {total > 0 && <Button variant="ghost" icon={<X />} onClick={() => onChange({ sort: search.sort, subtasks: search.subtasks })}>Clear filters</Button>}
      {!hideSort && (
        <div className="ml-auto">
          <Select value={search.sort ?? "-number"} onValueChange={(v) => v && set({ sort: v === "-number" ? undefined : v })} items={SORTS.map((s) => ({ value: s.value, label: `Sort: ${s.label}` }))}>
            <SelectTrigger aria-label="Sort" className="w-auto min-w-40"><SelectValue /></SelectTrigger>
            <SelectContent>{SORTS.map((s) => <SelectItem key={s.value} value={s.value}>Sort: {s.label}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      )}
    </div>
  )
}
