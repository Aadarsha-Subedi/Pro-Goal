import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Plus } from "@/icons"
import { suggestTaskKey } from "@/lib/format"
import { projectError, projectFieldError } from "./errors"
import { useProjectMutations } from "./queries"

export function CreateProjectDialog({ variant = "default" }: { variant?: "default" | "outline" }) {
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant={variant} icon={<Plus weight="bold" />}>New project</Button>} />
      <DialogContent><CreateBody onClose={() => setOpen(false)} /></DialogContent>
    </Dialog>
  )
}

// Mounted only while the dialog is open, so every opening starts empty.
function CreateBody({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("")
  const [key, setKey] = useState("")
  const [keyTouched, setKeyTouched] = useState(false)
  const [description, setDescription] = useState("")
  const [error, setError] = useState<unknown>(null)
  const { create } = useProjectMutations()
  const navigate = useNavigate()

  const submit = () => {
    setError(null)
    create.mutate(
      { name: name.trim(), task_key: key.toUpperCase(), description: description.trim() },
      {
        onSuccess: (p) => {
          onClose()
          navigate({ to: "/app/projects/$projectId", params: { projectId: p.id } })
        },
        onError: setError,
      },
    )
  }
  const keyOk = /^[A-Za-z]{2,5}$/.test(key)
  const nameError = projectFieldError(error, "name")
  const keyError = projectFieldError(error, "task_key")
  const generic = error && !nameError && !keyError && !projectFieldError(error, "description") ? projectError(error) : null

  return (
    <>
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
          <DialogDescription>You become the owner. Share the join code afterwards to bring people in.</DialogDescription>
        </DialogHeader>
        <form id="create-project" className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (name.trim() && keyOk) submit() }}>
          <Field data-invalid={!!nameError || undefined}>
            <FieldLabel htmlFor="project-name">Name</FieldLabel>
            <Input id="project-name" value={name} maxLength={120} autoFocus aria-invalid={!!nameError} onChange={(e) => { setName(e.target.value); if (!keyTouched) setKey(suggestTaskKey(e.target.value)) }} />
            {nameError && <FieldError>{nameError}</FieldError>}
          </Field>
          <Field data-invalid={!!keyError || undefined}>
            <FieldLabel htmlFor="project-key">Task key</FieldLabel>
            <Input id="project-key" value={key} maxLength={5} className="w-28! font-mono uppercase" aria-invalid={!!keyError} onChange={(e) => { setKeyTouched(true); setKey(e.target.value.replace(/[^a-zA-Z]/g, "")) }} />
            {keyError ? <FieldError>{keyError}</FieldError> : <FieldDescription>2 to 5 letters. Tasks read {key.toUpperCase() || "KEY"}-1, {key.toUpperCase() || "KEY"}-2.</FieldDescription>}
          </Field>
          <Field>
            <FieldLabel htmlFor="project-description">Description <span className="font-normal text-muted-foreground">(optional)</span></FieldLabel>
            <Textarea id="project-description" value={description} rows={3} maxLength={5000} onChange={(e) => setDescription(e.target.value)} />
          </Field>
          {generic && <p role="alert" className="text-sm text-destructive">{generic}</p>}
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onClose()}>Cancel</Button>
          <Button type="submit" form="create-project" icon={<Plus weight="bold" />} loading={create.isPending} disabled={!name.trim() || !keyOk}>Create project</Button>
        </DialogFooter>
    </>
  )
}
