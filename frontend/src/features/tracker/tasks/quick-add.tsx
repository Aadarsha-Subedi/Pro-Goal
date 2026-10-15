import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Lock, Plus } from "@/icons"
import { useLockText } from "@/features/permissions/use-lock-text"
import { trackerError } from "../errors"
import { useTaskMutations } from "../queries"

/** One line to add a task: title only. Status and priority take the project's defaults; the task page has the rest. */
export function QuickAdd({ projectId, parent, allowed, archived, placeholder = "Add a task", onAdded }: { projectId: string; parent?: number; allowed: boolean; archived?: boolean; placeholder?: string; onAdded?: (number: number) => void }) {
  const [title, setTitle] = useState("")
  const [error, setError] = useState<string | null>(null)
  const { create, createSubtask } = useTaskMutations(projectId)
  const pending = create.isPending || createSubtask.isPending
  const off = !allowed || archived
  const lockText = useLockText()

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const t = title.trim()
    if (!t || off) return
    setError(null)
    const done = { onSuccess: (task: { number: number; key: string }) => { setTitle(""); toast.success(`${task.key} added.`); onAdded?.(task.number) }, onError: (err: unknown) => setError(trackerError(err)) }
    if (parent) createSubtask.mutate({ parent, input: { title: t } }, done)
    else create.mutate({ title: t }, done)
  }

  return (
    <div className="space-y-1">
      <form onSubmit={submit} className="flex items-center gap-2">
        <Input value={title} onChange={(e) => { setTitle(e.target.value); setError(null) }} placeholder={off ? "Adding tasks is off for you" : placeholder} aria-label={placeholder} maxLength={255} disabled={off} aria-invalid={!!error} />
        <Button type="submit" icon={off ? <Lock /> : <Plus weight="bold" />} loading={pending} disabled={off || !title.trim()}>Add</Button>
      </form>
      {off && <p className="text-xs text-muted-foreground">{archived ? "This project is archived." : lockText("task.create")}</p>}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    </div>
  )
}
