import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { OptionsState } from "@/components/patterns/options-state"
import type { LazyOptions } from "@/lib/lazy-options"
import { cn } from "@/lib/utils"

const ALL = "__all"

/** A filter dropdown whose first choice clears it. The label names the filter even when a value is chosen. */
export function FilterSelect({ label, value, onChange, options, source, className }: { label: string; value?: string; onChange: (value: string | undefined) => void; options: { value: string; label: string }[]; /** Set when the options come from a request: it starts on first open and its loading and error states show in the list. */ source?: LazyOptions<unknown>; className?: string }) {
  const items = [{ value: ALL, label: `${label}: any` }, ...options.map((o) => ({ value: o.value, label: `${label}: ${o.label}` }))]
  return (
    <Select value={value ?? ALL} onValueChange={(v) => onChange(v === ALL || v == null ? undefined : v)} onOpenChange={(open) => open && source?.load()} items={items}>
      <SelectTrigger aria-label={`${label}: ${items.find((i) => i.value === (value ?? ALL))?.label.replace(`${label}: `, "") ?? "any"}`} className={cn("w-auto min-w-32 max-w-56", value && "border-primary/50", className)}><SelectValue /></SelectTrigger>
      <SelectContent className="w-max min-w-(--anchor-width) max-w-[min(24rem,90vw)]">{items.map((i) => <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>)}{source && <OptionsState source={source} />}</SelectContent>
    </Select>
  )
}
