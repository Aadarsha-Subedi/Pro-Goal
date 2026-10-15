import { useRef } from "react"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Textarea } from "@/components/ui/textarea"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { At } from "@/icons"
import type { Person } from "@/components/patterns/member-picker"

export interface PickedMention {
  id: string
  name: string
}

/** A text area with a Mention button. Picking a person inserts `@Name`; the caller turns picked names into wire tokens on submit. */
export function MentionTextarea({ value, onChange, people, onPick, label, rows = 3, maxLength, placeholder, disabled, autoFocus }: { value: string; onChange: (v: string) => void; people: Person[]; onPick: (m: PickedMention) => void; label: string; rows?: number; maxLength?: number; placeholder?: string; disabled?: boolean; autoFocus?: boolean }) {
  const area = useRef<HTMLTextAreaElement>(null)
  const insert = (p: Person) => {
    const el = area.current
    const at = el?.selectionStart ?? value.length
    const end = el?.selectionEnd ?? value.length
    const lead = at > 0 && !/\s/.test(value[at - 1]) ? " " : ""
    const next = `${value.slice(0, at)}${lead}@${p.name} ${value.slice(end)}`
    onChange(next)
    onPick({ id: p.id, name: p.name })
    requestAnimationFrame(() => {
      el?.focus()
      const pos = at + lead.length + p.name.length + 2
      el?.setSelectionRange(pos, pos)
    })
  }
  return (
    <div className="space-y-1.5">
      <Textarea ref={area} aria-label={label} value={value} rows={rows} maxLength={maxLength} placeholder={placeholder} disabled={disabled} autoFocus={autoFocus} onChange={(e) => onChange(e.target.value)} />
      <Popover>
        <PopoverTrigger render={<Button type="button" variant="ghost" size="sm" icon={<At />} disabled={disabled || people.length === 0}>Mention</Button>} />
        <PopoverContent align="start" className="w-60 gap-1 p-2">
          <p className="px-2 text-xs text-muted-foreground">They get an email.</p>
          <ul className="max-h-56 overflow-auto" aria-label="Members">
            {people.map((p) => (
              <li key={p.id}>
                <button type="button" className="flex min-h-8 w-full items-center gap-2 rounded-md px-2 text-left text-sm outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 pointer-coarse:min-h-11" onClick={() => insert(p)}>
                  <UserAvatar name={p.name} src={p.avatar_url} size="sm" /><span className="truncate">{p.name}</span>
                </button>
              </li>
            ))}
          </ul>
        </PopoverContent>
      </Popover>
    </div>
  )
}
