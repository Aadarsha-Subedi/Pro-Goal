import { useRouter } from "@tanstack/react-router"
import { useRef, useState } from "react"
import { toast } from "sonner"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Button } from "@/components/ui/button"
import type { Me } from "@/features/auth/api"
import { TextField } from "@/features/auth/fields"
import { Check, Image as ImageIcon, Trash } from "@/icons"
import { ApiError } from "@/lib/api"
import { accountApi } from "./api"
import { accountError } from "./errors"

const MAX_AVATAR = 5 * 1024 * 1024
const NAME_MAX = 50

/** Name, display name and picture. The shell reads `me` from the router, so a save refreshes it everywhere. */
export function ProfileSection({ me }: { me: Me }) {
  const router = useRouter()
  const [first, setFirst] = useState(me.first_name)
  const [last, setLast] = useState(me.last_name)
  const [display, setDisplay] = useState(me.display_name)
  const [busy, setBusy] = useState(false)
  const [avatarBusy, setAvatarBusy] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const input = useRef<HTMLInputElement>(null)
  const dirty = first.trim() !== me.first_name || last.trim() !== me.last_name || display.trim() !== me.display_name
  const ready = first.trim() && display.trim()

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!ready) return
    setBusy(true)
    setErrors({})
    try {
      await accountApi.updateProfile({ first_name: first.trim(), last_name: last.trim(), display_name: display.trim() })
      await router.invalidate()
      toast.success("Profile saved.")
    } catch (err) {
      if (err instanceof ApiError && err.errors.length) setErrors(Object.fromEntries(err.errors.map((x) => [x.field, x.message])))
      else toast.error(accountError(err))
    } finally {
      setBusy(false)
    }
  }

  const pick = async (file: File | undefined) => {
    if (!file) return
    if (!/^image\/(jpeg|png|webp)$/.test(file.type)) return void toast.error("Choose a JPEG, PNG or WebP picture.")
    if (file.size > MAX_AVATAR) return void toast.error("That picture is over 5 MB. Choose a smaller one.")
    setAvatarBusy(true)
    try {
      await accountApi.uploadAvatar(file)
      await router.invalidate()
      toast.success("Picture updated.")
    } catch (err) {
      toast.error(accountError(err))
    } finally {
      setAvatarBusy(false)
      if (input.current) input.current.value = ""
    }
  }
  const remove = async () => {
    setAvatarBusy(true)
    try {
      await accountApi.removeAvatar()
      await router.invalidate()
      toast.success("Picture removed.")
    } catch (err) {
      toast.error(accountError(err))
    } finally {
      setAvatarBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <UserAvatar name={me.display_name} src={me.avatar_url} size="lg" />
        <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" tabIndex={-1} aria-label="Choose a profile picture" onChange={(e) => void pick(e.target.files?.[0])} />
        <Button variant="outline" icon={<ImageIcon />} loading={avatarBusy} onClick={() => input.current?.click()}>{me.avatar_url ? "Change picture" : "Add a picture"}</Button>
        {me.avatar_url && <Button variant="ghost" icon={<Trash />} disabled={avatarBusy} onClick={remove}>Remove</Button>}
        <p className="basis-full text-xs text-muted-foreground">JPEG, PNG or WebP, up to 5 MB. It is cropped and resized for you.</p>
      </div>
      <form onSubmit={save} noValidate className="grid max-w-md gap-3">
        <TextField label="First name" value={first} maxLength={NAME_MAX} autoComplete="given-name" onChange={(e) => setFirst(e.target.value)} error={errors.first_name} />
        <TextField label="Last name" value={last} maxLength={NAME_MAX} autoComplete="family-name" onChange={(e) => setLast(e.target.value)} error={errors.last_name} />
        <TextField label="Display name" hint="What teammates see next to your work." value={display} maxLength={NAME_MAX} autoComplete="nickname" onChange={(e) => setDisplay(e.target.value)} error={errors.display_name} />
        <div><Button type="submit" icon={<Check weight="bold" />} loading={busy} disabled={!dirty || !ready}>Save profile</Button></div>
      </form>
    </div>
  )
}
