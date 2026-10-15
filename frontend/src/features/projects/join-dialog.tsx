import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog"
import { UserPlus } from "@/icons"
import { JoinForm } from "./join-form"

export function JoinProjectDialog({ variant = "outline" }: { variant?: "outline" | "default" }) {
  const [open, setOpen] = useState(false)
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant={variant} icon={<UserPlus />}>Join project</Button>} />
      <DialogContent><JoinForm onDone={() => setOpen(false)} /></DialogContent>
    </Dialog>
  )
}
