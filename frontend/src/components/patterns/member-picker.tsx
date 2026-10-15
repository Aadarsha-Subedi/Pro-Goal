import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { UserPlus } from "@/icons"

export interface Person {
  id: string
  name: string
  avatar_url?: string | null
}

/** Pick several people. The trigger lists who is chosen in words, so the value is never only a row of faces. */
export function MemberPicker({ people, value, onChange, disabled, id, placeholder = "Unassigned" }: { people: Person[]; value: string[]; onChange: (ids: string[]) => void; disabled?: boolean; id?: string; placeholder?: string }) {
  const [filter, setFilter] = useState("")
  const chosen = people.filter((p) => value.includes(p.id))
  const shown = people.filter((p) => p.name.toLowerCase().includes(filter.trim().toLowerCase()))
  const toggle = (pid: string) => onChange(value.includes(pid) ? value.filter((v) => v !== pid) : [...value, pid])
  const label = chosen.length === 0 ? placeholder : chosen.length <= 2 ? chosen.map((p) => p.name).join(", ") : `${chosen[0].name} and ${chosen.length - 1} more`
  return (
    <Popover onOpenChange={(o) => !o && setFilter("")}>
      <PopoverTrigger render={<Button id={id} variant="outline" disabled={disabled} className="max-w-full justify-start font-normal" icon={<UserPlus />}><span className={chosen.length === 0 ? "truncate text-muted-foreground" : "truncate"}>{label}</span></Button>} />
      <PopoverContent align="start" className="w-64 gap-2 p-2">
        {people.length > 6 && <Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Find a person" aria-label="Find a person" />}
        <ul className="max-h-60 space-y-0.5 overflow-auto" aria-label="Members">
          {shown.length === 0 && <li className="px-2 py-1.5 text-sm text-muted-foreground">No one matches.</li>}
          {shown.map((p) => (
            <li key={p.id}>
              <label className="flex min-h-8 cursor-pointer items-center gap-2 rounded-md px-2 text-sm hover:bg-muted pointer-coarse:min-h-11">
                <Checkbox checked={value.includes(p.id)} onCheckedChange={() => toggle(p.id)} />
                <UserAvatar name={p.name} src={p.avatar_url} size="sm" />
                <span className="truncate">{p.name}</span>
              </label>
            </li>
          ))}
        </ul>
        {value.length > 0 && <Button size="sm" variant="ghost" className="justify-start" onClick={() => onChange([])}>Clear all</Button>}
      </PopoverContent>
    </Popover>
  )
}
