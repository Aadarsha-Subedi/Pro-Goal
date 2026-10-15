import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { CalendarBlank, X } from "@/icons"

const toDate = (v?: string | null) => {
  if (!v) return undefined
  const [y, m, d] = v.split("-").map(Number)
  return new Date(y, m - 1, d)
}
const toPlain = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`

interface DatePickerProps {
  placeholder?: string
  /** Plain date ("2026-10-10", no time zone). Omit to let the picker keep its own state. */
  value?: string | null
  onChange?: (value: string | null) => void
  disabled?: boolean
  id?: string
}

/** Plain-date picker. Dates carry no time zone, so the value is a "YYYY-MM-DD" string, never a Date. */
export function DatePicker({ placeholder = "Pick a date", value, onChange, disabled, id }: DatePickerProps) {
  const [own, setOwn] = useState<string | null>(null)
  const controlled = value !== undefined
  const current = toDate(controlled ? value : own)
  const [open, setOpen] = useState(false)
  const set = (d?: Date) => {
    setOpen(false)
    const next = d ? toPlain(d) : null
    if (!controlled) setOwn(next)
    onChange?.(next)
  }
  return (
    <div className="flex items-center gap-1">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger render={<Button id={id} variant="outline" disabled={disabled} className="w-44 justify-start font-normal" icon={<CalendarBlank />}>{current ? current.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : <span className="text-muted-foreground">{placeholder}</span>}</Button>} />
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar mode="single" selected={current} onSelect={set} defaultMonth={current} />
        </PopoverContent>
      </Popover>
      {current && !disabled && <Button variant="ghost" size="icon" label="Clear date" onClick={() => set(undefined)}><X /></Button>}
    </div>
  )
}
