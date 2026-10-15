import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Copy } from "@/icons"
import type { Project } from "./api"
import { projectError, projectFieldError } from "./errors"
import { useProjectMutations } from "./queries"

/** Copies a shared demo project into a project the caller owns and can edit. */
export function CopyProjectDialog({ project, variant = "default", size }: { project: Project; variant?: "default" | "outline"; size?: "sm" }) {
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant={variant} size={size} icon={<Copy />} data-tour="copy-project">Copy to my workspace</Button>} />
      <DialogContent><CopyBody project={project} onClose={() => setOpen(false)} /></DialogContent>
    </Dialog>
  )
}

// Mounted only while the dialog is open, so every opening starts from the default name.
function CopyBody({ project, onClose }: { project: Project; onClose: () => void }) {
  const [name, setName] = useState(`${project.name} (copy)`.slice(0, 120))
  const [error, setError] = useState<unknown>(null)
  const { copy } = useProjectMutations(project.id)
  const navigate = useNavigate()
  const nameError = projectFieldError(error, "name")

  const submit = () => {
    setError(null)
    copy.mutate(name.trim() || undefined, {
      onSuccess: (p) => {
        onClose()
        toast.success("Copied. This one is yours to edit.")
        navigate({ to: "/app/projects/$projectId", params: { projectId: p.id } })
      },
      onError: setError,
    })
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Copy to my workspace</DialogTitle>
        <DialogDescription>You get your own copy with the same statuses, tasks, notes and comments. You own it, so you can change anything. The demo stays as it is.</DialogDescription>
      </DialogHeader>
      <form id="copy-project" className="space-y-3" onSubmit={(e) => { e.preventDefault(); submit() }}>
        <Field data-invalid={!!nameError || undefined}>
          <FieldLabel htmlFor="copy-name">Name</FieldLabel>
          <Input id="copy-name" value={name} maxLength={120} autoFocus aria-invalid={!!nameError} onChange={(e) => setName(e.target.value)} />
          {nameError ? <FieldError>{nameError}</FieldError> : <FieldDescription>You can rename it later.</FieldDescription>}
        </Field>
        {error != null && !nameError && <p role="alert" className="text-sm text-destructive">{projectError(error)}</p>}
      </form>
      <DialogFooter>
        <Button variant="outline" onClick={() => onClose()}>Cancel</Button>
        <Button type="submit" form="copy-project" icon={<Copy />} loading={copy.isPending}>Make my copy</Button>
      </DialogFooter>
    </>
  )
}
