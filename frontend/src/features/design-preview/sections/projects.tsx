import { useState } from "react"
import { FileDropzone } from "@/components/patterns/file-dropzone"
import { UsageMeter } from "@/components/patterns/usage-meter"
import { FilterSelect } from "@/components/patterns/filter-select"
import { MemberPicker } from "@/components/patterns/member-picker"
import { PropertyRow } from "@/components/patterns/property-row"
import { PriorityTag, StatusTag } from "@/components/patterns/work-status"
import { PageHeader } from "@/components/patterns/page-header"
import { StatusBanner } from "@/components/patterns/status-banner"
import { UserAvatar } from "@/components/patterns/user-avatar"
import { Button } from "@/components/ui/button"
import { ReauthDialog } from "@/features/projects/reauth-dialog"
import { ArrowCounterClockwise, Archive, Check, CheckCircle, Crown, Desktop, DotsThree, Lock, Minus, Plus, SignIn, SignOut, Trash, Users, WarningCircle, X, XCircle } from "@/icons"
import { Checkbox } from "@/components/ui/checkbox"
import { Switch } from "@/components/ui/switch"
import { Globe, Hash, Plugs, SlackLogo } from "@/icons"
import { Section, Specimen } from "../section"

/** Project surfaces for Feature 2. Static data: no network calls. */
export function ProjectSurfaces() {
  const [reauth, setReauth] = useState(false)
  return (
    <Section id="projects" title="Project surfaces" intro="Page header, state banners, member and request rows, and the re-authentication dialog for owner-only actions. All flat: hairlines and tone, no boxes.">
      <Specimen title="Page header" note="One h1, one line of context, actions on the right. The primary action is the only filled button on the page.">
        <PageHeader title="Projects" description="Every project is its own space with its own members and permissions." actions={<><Button variant="outline" icon={<Users />}>Join project</Button><Button icon={<Plus weight="bold" />}>New project</Button></>} />
      </Specimen>

      <Specimen title="State banners" note="Archived, scheduled for deletion, info. Icon, one sentence, one action, hairline below.">
        <div className="max-w-2xl space-y-4">
          <StatusBanner tone="warning" title="Archived." action={<Button size="sm" variant="outline" icon={<Archive />}>Unarchive</Button>}>This project is read-only for everyone until the owner unarchives it.</StatusBanner>
          <StatusBanner tone="danger" title="Scheduled for deletion." action={<Button size="sm" icon={<ArrowCounterClockwise />}>Restore project</Button>}>It is deleted for good in 6 days. Members can't open it.</StatusBanner>
          <StatusBanner tone="info" title="Offer sent to Sam.">It expires in 7 days.</StatusBanner>
        </div>
      </Specimen>

      <Specimen title="Member row" note="Name and email (owner view), role as icon plus text, actions in a menu. Rows divide, they do not box.">
        <ul className="max-w-2xl divide-y border-y">
          {[["Maya Chen", "maya@example.com", true], ["Sam Okafor", "sam@example.com", false]].map(([n, e, owner]) => (
            <li key={String(n)} className="flex min-h-14 items-center gap-3 py-2">
              <UserAvatar name={String(n)} />
              <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{n}</p><p className="truncate text-xs text-muted-foreground">{e} · Joined 3 Oct 2026</p></div>
              {owner ? <span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Crown weight="fill" className="size-3.5 text-warning" />Owner</span> : <span className="text-xs text-muted-foreground">Member</span>}
              {owner ? <span className="size-(--ctl-h)" aria-hidden /> : <Button variant="ghost" size="icon" label={`Actions for ${n}`}><DotsThree weight="bold" /></Button>}
            </li>
          ))}
        </ul>
      </Specimen>

      <Specimen title="Join request row" note="Approve opens a preset picker; Decline is immediate and tells the owner the person may ask again in 24 hours.">
        <ul className="max-w-2xl divide-y border-y">
          <li className="flex flex-wrap items-center gap-x-3 gap-y-2 py-3">
            <UserAvatar name="Liam Park" />
            <div className="min-w-0 flex-1 basis-48"><p className="truncate text-sm font-medium">Liam Park</p><p className="truncate text-xs text-muted-foreground">liam@example.com · asked 9 Oct 2026 · expires in 12 days</p></div>
            <div className="flex gap-2"><Button size="sm" variant="outline" icon={<X />}>Decline</Button><Button size="sm" icon={<Check weight="bold" />}>Approve…</Button></div>
          </li>
        </ul>
      </Specimen>

      <Specimen title="Task row" note="Key, title with context, status, priority, people, due date. Status and priority come from the project's own lists: icon from the status group, text from its name. Overdue is icon plus text.">
        <ul className="max-w-4xl divide-y border-y">
          {[
            ["APL-12", "Draft launch checklist", "To do", "todo", "Medium", 2, "Unassigned", "No due date", false],
            ["APL-13", "Book venue", "In progress", "in_progress", "Urgent", 4, "Maya", "Overdue · 8 Oct 2026", true],
            ["APL-14", "Collect requirements", "Done", "done", "Low", 1, "Sam", "3 Oct 2026", false],
          ].map(([key, title, status, cat, pri, rank, who, due, late]) => (
            <li key={String(key)} className="flex min-h-(--row-h) flex-wrap items-center gap-x-4 gap-y-1 px-1 py-2">
              <span className="w-20 font-mono text-xs text-muted-foreground">{key}</span>
              <span className="min-w-0 flex-1 basis-56 truncate text-sm font-medium">{title}</span>
              <StatusTag name={String(status)} category={cat as "todo"} className="w-32" />
              <PriorityTag name={String(pri)} rank={Number(rank)} max={4} className="w-24" />
              <span className="w-20 text-xs text-muted-foreground">{who}</span>
              <span className={`w-44 text-xs ${late ? "font-medium text-destructive" : "text-muted-foreground"}`}>{due}</span>
            </li>
          ))}
        </ul>
      </Specimen>

      <Specimen title="Properties and filters" note="Each property locks with its reason beside it. Filter selects name the filter even when a value is chosen.">
        <div className="max-w-xl divide-y border-y">
          <PropertyRow label="Status"><StatusTag name="In progress" category="in_progress" /></PropertyRow>
          <PropertyRow label="Assignees"><MemberPicker people={[{ id: "1", name: "Maya Chen" }, { id: "2", name: "Sam Okafor" }]} value={["1"]} onChange={() => {}} /></PropertyRow>
          <PropertyRow label="Due date" lockedBy="Needs “Change due date”. Ask Ada or a member who manages permissions."><span className="text-sm">8 Oct 2026</span></PropertyRow>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <FilterSelect label="Status" value="a" onChange={() => {}} options={[{ value: "a", label: "In progress" }]} />
          <FilterSelect label="Priority" onChange={() => {}} options={[{ value: "a", label: "Urgent" }]} />
        </div>
      </Specimen>

      <Specimen title="Files and storage" note="Drop zone, an upload in progress, a failed one with its reason and Retry, and usage in words. The state is never colour alone.">
        <div className="max-w-2xl space-y-4">
          <FileDropzone compact onFiles={() => {}} />
          <ul className="divide-y border-y">
            <li className="flex min-h-12 items-center gap-3 py-1.5"><span className="min-w-0 flex-1"><p className="truncate text-sm font-medium">roadmap.pdf</p><p role="status" className="text-xs text-muted-foreground">Uploading 62%</p><div className="mt-1 h-1 overflow-hidden rounded-full bg-muted"><div className="h-full w-[62%] bg-primary" /></div></span></li>
            <li className="flex min-h-12 items-center gap-3 py-1.5"><span className="min-w-0 flex-1"><p className="truncate text-sm font-medium">demo.mov</p><p role="alert" className="text-xs text-destructive">demo.mov isn't an allowed file type. Images, PDF, Word, Excel, PowerPoint, text and MP3 or M4A audio only.</p></span></li>
          </ul>
          <UsageMeter label="This project" used={412 * 1024 * 1024} limit={1024 * 1024 * 1024} format={(n) => `${Math.round(n / 1048576)} MB`} />
          <UsageMeter label="Your files" used={92 * 1024 * 1024} limit={100 * 1024 * 1024} format={(n) => `${Math.round(n / 1048576)} MB`} />
        </div>
      </Specimen>

      <Specimen title="Permission editor" note="Flat checkbox rows with the registry's label and description. A row you don't hold is disabled and says why; a changed row says what will happen; the footer states the diff.">
        <div className="max-w-2xl space-y-3">
          <div className="flex items-baseline justify-between border-b pb-2"><h3 className="text-sm font-semibold">Tasks</h3><p className="text-xs tabular-nums text-muted-foreground">2 of 3</p></div>
          <ul className="divide-y">
            <li className="flex items-start gap-3 py-2.5"><Checkbox checked className="mt-0.5" aria-label="Create tasks" /><div className="flex-1"><p className="text-sm font-medium">Create tasks</p><p className="text-xs text-muted-foreground">Add tasks and subtasks.</p></div></li>
            <li className="flex items-start gap-3 py-2.5"><Checkbox className="mt-0.5" aria-label="Delete tasks" /><div className="flex-1"><p className="text-sm font-medium">Delete tasks</p><p className="text-xs text-muted-foreground">Move tasks to the trash.</p></div><span className="inline-flex items-center gap-1 text-xs text-muted-foreground"><Plus className="size-3" aria-hidden />Will add</span></li>
            <li className="flex items-start gap-3 py-2.5"><Checkbox checked disabled className="mt-0.5" aria-label="Change due date" /><div className="flex-1"><p className="text-sm font-medium">Change due date</p><p className="text-xs text-muted-foreground">Set or clear the due date. <span className="inline-flex items-center gap-1"><Lock className="size-3" aria-hidden />You don't hold this one.</span></p></div></li>
          </ul>
          <div className="flex items-center gap-3 border-t pt-3"><p className="flex-1 text-sm"><span className="font-medium">Adds 1.</span> <span className="text-muted-foreground">+ Delete tasks</span></p><Button variant="ghost">Discard</Button><Button icon={<Check weight="bold" />}>Save permissions</Button></div>
        </div>
      </Specimen>

      <Specimen title="Who can change what" note="Members as columns, groups as rows, every cell icon plus text. Opens to single permissions; scrolls inside its own region.">
        <div className="max-w-2xl overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left"><th className="py-2 pr-4 font-medium">Area</th><th className="px-3 font-medium">Olive (owner)</th><th className="px-3 font-medium">Sam</th></tr></thead><tbody className="divide-y">
          <tr><th scope="row" className="py-2 pr-4 text-left font-medium">Tasks</th><td className="px-3"><span className="inline-flex items-center gap-1"><Check weight="bold" className="size-3.5" aria-hidden />All</span></td><td className="px-3"><span className="inline-flex items-center gap-1 tabular-nums"><Minus weight="bold" className="size-3.5" aria-hidden />2 of 9</span></td></tr>
          <tr><th scope="row" className="py-2 pr-4 text-left font-medium">Members</th><td className="px-3"><span className="inline-flex items-center gap-1"><Check weight="bold" className="size-3.5" aria-hidden />All</span></td><td className="px-3 text-muted-foreground"><span className="inline-flex items-center gap-1"><Minus className="size-3.5" aria-hidden />None</span></td></tr>
        </tbody></table></div>
      </Specimen>

      <Specimen title="Devices and security log" note="This device is icon plus text with no button. Events that need a second look carry a warning icon and words. Rows divide, they do not box.">
        <ul className="max-w-2xl divide-y border-y">
          <li className="flex min-h-14 items-center gap-3 py-2"><Desktop className="size-5 text-muted-foreground" aria-hidden /><div className="flex-1"><p className="text-sm font-medium">Chrome on Linux <span className="inline-flex items-center gap-1 text-xs font-normal text-muted-foreground"><CheckCircle weight="fill" className="size-3.5 text-success" aria-hidden />This device</span></p><p className="text-xs text-muted-foreground">127.0.0.1 · Last active 10 Oct 2026, 5:13 PM</p></div></li>
          <li className="flex min-h-14 items-center gap-3 py-2"><Desktop className="size-5 text-muted-foreground" aria-hidden /><div className="flex-1"><p className="text-sm font-medium">Safari on iPhone</p><p className="text-xs text-muted-foreground">203.0.113.8 · Last active 8 Oct 2026, 9:02 AM</p></div><Button variant="outline" size="sm" icon={<SignOut />}>Sign out</Button></li>
          <li className="flex min-h-12 items-center gap-3 py-2"><SignIn className="size-4 text-muted-foreground" aria-hidden /><div className="flex-1"><p className="text-sm font-medium">Signed in</p><p className="text-xs text-muted-foreground">Chrome on Linux · 10 Oct 2026, 2:59 PM</p></div></li>
          <li className="flex min-h-12 items-center gap-3 py-2"><WarningCircle className="size-4 text-muted-foreground" aria-hidden /><div className="flex-1"><p className="text-sm font-medium">Wrong password</p><p className="text-xs text-muted-foreground">Unknown device · 9 Oct 2026, 11:40 PM</p></div><span className="inline-flex items-center gap-1 text-xs text-warning-text"><WarningCircle weight="fill" className="size-3.5 text-warning" aria-hidden />Check this was you</span></li>
        </ul>
        <div className="mt-4 max-w-md flex gap-2.5 border-y py-3 text-sm" role="alert"><XCircle weight="fill" className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden /><div><p className="font-medium">Account locked for now</p><p className="text-muted-foreground">Too many wrong passwords. Try again in about 14 minutes, or <span className="font-medium text-primary underline underline-offset-4">reset your password</span>.</p></div></div>
      </Specimen>

      <Specimen title="Integration and channels" note="Status is icon plus text. A public channel says who can read the posts. A needs-attention integration says why sending stopped and offers Reconnect.">
        <div className="max-w-2xl space-y-4">
          <StatusBanner tone="warning" title="Slack stopped sending." action={<Button size="sm" icon={<Plugs />}>Reconnect Slack</Button>}>10 deliveries in a row failed. Waiting messages go out once you reconnect.</StatusBanner>
          <div className="flex flex-wrap items-center gap-3 border-b pb-3"><SlackLogo className="size-6 text-muted-foreground" aria-hidden /><div className="min-w-0 flex-1"><p className="flex items-center gap-2 text-sm font-semibold">Slack <span className="inline-flex items-center gap-1 text-xs font-normal text-muted-foreground"><WarningCircle weight="fill" className="size-3.5 text-warning" aria-hidden />Needs attention</span></p><p className="text-xs text-muted-foreground">Workspace T01ABC · connected by Olive · since 9 Oct 2026</p></div><Button variant="outline" size="sm">Delivery log</Button><Button variant="outline" size="sm" icon={<Plugs />}>Disconnect</Button></div>
          <ul className="divide-y border-y">
            <li className="flex min-h-14 items-center gap-3 py-2"><Hash className="size-4 text-muted-foreground" aria-hidden /><div className="flex-1"><p className="flex items-center gap-2 text-sm font-medium">launch-updates <span className="inline-flex items-center gap-1 text-xs font-normal text-muted-foreground"><Globe className="size-3.5" aria-hidden />Public channel</span></p><p className="text-xs text-muted-foreground">3 events: Task created, Task assigned, New comment</p><p className="mt-0.5 flex items-center gap-1 text-xs text-warning-text"><WarningCircle weight="fill" className="size-3.5 text-warning" aria-hidden />Anyone in the workspace can read these posts.</p></div><Button variant="ghost" size="sm">Events</Button></li>
          </ul>
        </div>
      </Specimen>

      <Specimen title="Delivery log and notifications" note="Each delivery: event, outcome as icon plus text, attempt, the server's answer. Notification switches are labelled per event and per channel.">
        <div className="max-w-2xl space-y-4">
          <ul className="divide-y border-y">
            <li className="flex min-h-14 items-center gap-3 py-2"><div className="flex-1"><p className="flex items-center gap-3 text-sm font-medium">Task assigned <span className="inline-flex items-center gap-1 text-xs font-normal text-destructive"><XCircle weight="fill" className="size-3.5" aria-hidden />Failed</span></p><p className="text-xs text-muted-foreground">10 Oct 2026, 4:02 PM · Attempt 6 of 6 · Answer 429</p></div><Button variant="outline" size="sm">Send again</Button></li>
            <li className="flex min-h-14 items-center gap-3 py-2"><div className="flex-1"><p className="flex items-center gap-3 text-sm font-medium">New comment <span className="inline-flex items-center gap-1 text-xs font-normal text-muted-foreground"><CheckCircle weight="fill" className="size-3.5 text-success" aria-hidden />Delivered</span></p><p className="text-xs text-muted-foreground">10 Oct 2026, 3:58 PM · Attempt 1 of 6 · Answer 200</p></div></li>
          </ul>
          <table className="w-full text-sm"><thead><tr className="border-b text-left text-xs text-muted-foreground"><th className="py-2 pr-3 font-medium">Event</th><th className="px-3 font-medium">Email</th><th className="pl-3 font-medium">Slack message</th></tr></thead><tbody className="divide-y"><tr><th scope="row" className="py-2.5 pr-3 text-left font-normal">Task assigned</th><td className="px-3"><Switch defaultChecked aria-label="Email me: Task assigned" /></td><td className="pl-3"><Switch defaultChecked aria-label="Slack message: Task assigned" /></td></tr></tbody></table>
        </div>
      </Specimen>

      <Specimen title="Re-authentication" note="Sensitive owner actions ask for the password, or a fresh Google sign-in. Extra fields (typed name, recipient) sit above the password.">
        <Button variant="destructive" icon={<Trash />} onClick={() => setReauth(true)}>Delete project…</Button>
        <ReauthDialog open={reauth} onOpenChange={setReauth} title="Delete Apollo?" description="12 members lose access now. You can restore the project during the next 7 days." confirmLabel="Delete project" variant="solid-destructive" icon={<Trash />} onConfirm={async () => { await new Promise((r) => setTimeout(r, 400)) }} />
      </Specimen>
    </Section>
  )
}
