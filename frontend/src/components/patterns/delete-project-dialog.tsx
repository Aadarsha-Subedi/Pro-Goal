import { useState } from "react"
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Trash, Warning } from "@/icons"

/** Most destructive action in the product: typed project name plus password, solid red confirm. */
export function DeleteProjectDialog({ name = "Apollo", members = 12, tasks = 248, files = 31 }: { name?: string; members?: number; tasks?: number; files?: number }) {
  const [typed, setTyped] = useState("")
  const [password, setPassword] = useState("")
  const ready = typed === name && password.length > 0
  return (
    <AlertDialog onOpenChange={(o) => { if (!o) { setTyped(""); setPassword("") } }}>
      <AlertDialogTrigger render={<Button variant="destructive" icon={<Trash />}>Delete project…</Button>} />
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete {name}?</AlertDialogTitle>
          <AlertDialogDescription>
            {members} members lose access now. {tasks} tasks and {files} files are kept for 7 days, then deleted permanently. You can restore the project during those 7 days.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="space-y-3">
          <Field>
            <FieldLabel htmlFor="del-name">Type <span className="font-mono">{name}</span> to confirm</FieldLabel>
            <Input id="del-name" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
          </Field>
          <Field>
            <FieldLabel htmlFor="del-pw">Confirm with your password</FieldLabel>
            <Input id="del-pw" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </Field>
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <Button variant="solid-destructive" icon={<Warning />} disabled={!ready}>Delete project</Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
