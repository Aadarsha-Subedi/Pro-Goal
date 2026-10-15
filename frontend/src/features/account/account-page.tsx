import { useRouteContext } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { PageHeader } from "@/components/patterns/page-header"
import { UsageMeter } from "@/components/patterns/usage-meter"
import { FilterSelect } from "@/components/patterns/filter-select"
import { formatBytes } from "@/features/attachments/limits"
import { useMyUsage } from "@/features/attachments/queries"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import { useDocumentTitle } from "@/hooks/use-document-title"
import { ArrowClockwise, ArrowLeft, ArrowRight, CheckCircle, Desktop, SignOut, WarningCircle, X } from "@/icons"
import { formatDateTime, plural } from "@/lib/format"
import { slackReturn } from "@/features/integrations/errors"
import { NotificationsSection, SlackLinkSection } from "@/features/integrations/slack-account"
import { PAGE_SIZE, type SecurityEventType } from "./api"
import { accountError } from "./errors"
import { DeleteSection } from "./delete-section"
import { EmailSection } from "./email-section"
import { PasswordSection } from "./password-section"
import { ProfileSection } from "./profile-section"
import { eventInfo, EVENT_OPTIONS } from "./events"
import { useRevokeSession, useSecurityEvents, useSessions } from "./queries"

export interface AccountSearch {
  type?: SecurityEventType
  page?: number
  /** Result Slack reports when it sends the browser back after linking. Shown once, then cleared. */
  slack?: string
  reason?: string
}

export function validateAccountSearch(s: Record<string, unknown>): AccountSearch {
  const page = Number(s.page)
  const type = EVENT_OPTIONS.find((o) => o.value === s.type)?.value
  const t = (v: unknown) => (typeof v === "string" && /^[a-z_]{1,40}$/.test(v) ? v : undefined)
  return { type, page: Number.isInteger(page) && page > 1 && page <= 10_000 ? page : undefined, slack: t(s.slack), reason: t(s.reason) }
}

function Section({ id, title, description, children }: { id: string; title: string; description: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="grid gap-4 border-t pt-6 lg:grid-cols-[16rem_1fr] lg:gap-8">
      <div className="space-y-1">
        <h2 id={id} className="text-sm font-semibold">{title}</h2>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  )
}

function Retry({ label, onRetry }: { label: string; onRetry: () => void }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <Button size="sm" variant="outline" icon={<ArrowClockwise />} onClick={onRetry}>Try again</Button>
    </div>
  )
}

function Sessions() {
  const { data, isPending, isError, refetch } = useSessions()
  const revoke = useRevokeSession()
  const [busy, setBusy] = useState<string | null>(null)
  if (isPending) return <div aria-busy="true" aria-label="Loading sessions" className="space-y-2"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>
  if (isError) return <Retry label="Couldn't load your sessions." onRetry={() => refetch()} />
  const end = (id: string, name: string) => {
    setBusy(id)
    revoke.mutate(id, {
      onSuccess: () => toast.success(`${name} was signed out.`),
      onError: (e) => toast.error(accountError(e)),
      onSettled: () => setBusy(null),
    })
  }
  return (
    <ul className="divide-y border-y" aria-label="Signed-in devices">
      {data.items.map((s) => {
        const name = s.device_name || "Unknown device"
        return (
          <li key={s.id} className="flex min-h-14 flex-wrap items-center gap-x-3 gap-y-1 py-2">
            <Desktop className="size-5 shrink-0 text-muted-foreground" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="flex flex-wrap items-center gap-x-2 text-sm font-medium">
                <span className="truncate">{name}</span>
                {s.is_current && <span className="inline-flex items-center gap-1 text-xs font-normal text-muted-foreground"><CheckCircle weight="fill" className="size-3.5 text-success" aria-hidden />This device</span>}
              </p>
              <p className="text-xs text-muted-foreground">{s.ip ? `${s.ip} · ` : ""}Last active {formatDateTime(s.last_seen_at)} · Signed in {formatDateTime(s.created_at)}{s.remember_me ? " · Kept for 30 days" : ""}</p>
            </div>
            {!s.is_current && (
              <Button variant="outline" size="sm" icon={<SignOut />} loading={busy === s.id} disabled={busy !== null} onClick={() => end(s.id, name)}>Sign out</Button>
            )}
          </li>
        )
      })}
    </ul>
  )
}

function SecurityLog({ search, onSearch }: { search: AccountSearch; onSearch: (next: AccountSearch) => void }) {
  const page = search.page ?? 1
  const { data, isPending, isError, isFetching, refetch } = useSecurityEvents(search.type, page)
  const count = data?.meta.count ?? 0
  const lastPage = Math.max(1, Math.ceil(count / PAGE_SIZE))
  const overshoot = !!data && data.items.length === 0 && count > 0 && page > lastPage
  useEffect(() => {
    if (overshoot) onSearch({ ...search, page: lastPage > 1 ? lastPage : undefined })
  }, [overshoot, lastPage, search, onSearch])

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <FilterSelect label="Event" value={search.type} onChange={(type) => onSearch({ type: type as SecurityEventType | undefined })} options={EVENT_OPTIONS} />
        {search.type && <Button variant="ghost" icon={<X />} onClick={() => onSearch({})}>Clear filter</Button>}
      </div>
      {isPending ? (
        <ul className="divide-y border-y" aria-busy="true" aria-label="Loading security log">{[0, 1, 2, 3].map((i) => <li key={i} className="py-3"><Skeleton className="h-4 w-64" /></li>)}</ul>
      ) : isError ? (
        <Retry label="Couldn't load the security log." onRetry={() => refetch()} />
      ) : data.items.length === 0 && !overshoot ? (
        <Empty><EmptyHeader><EmptyTitle>{search.type ? "Nothing of that kind" : "Nothing recorded yet"}</EmptyTitle><EmptyDescription>{search.type ? "Pick another event, or clear the filter." : "Sign-ins, password changes and ended sessions show up here for 180 days."}</EmptyDescription></EmptyHeader></Empty>
      ) : (
        <ul className="divide-y border-y" aria-label="Security log" aria-busy={isFetching}>
          {data.items.map((e) => {
            const info = eventInfo(e)
            const Icon = info.icon
            return (
              <li key={e.id} className="flex min-h-12 items-center gap-3 py-2">
                <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{info.label}</p>
                  <p className="text-xs text-muted-foreground">{[e.device_name, e.ip].filter(Boolean).join(" · ") || "No device recorded"} · {formatDateTime(e.created_at)}</p>
                </div>
                {info.attention && <span className="inline-flex shrink-0 items-center gap-1 text-xs text-warning-text"><WarningCircle weight="fill" className="size-3.5 text-warning" aria-hidden />Check this was you</span>}
              </li>
            )
          })}
        </ul>
      )}
      {data && count > PAGE_SIZE && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">{(page - 1) * PAGE_SIZE + 1} to {Math.min(page * PAGE_SIZE, count)} of {plural(count, "event")}</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" icon={<ArrowLeft />} disabled={page <= 1} onClick={() => onSearch({ ...search, page: page > 2 ? page - 1 : undefined })}>Previous</Button>
            <Button variant="outline" size="sm" iconEnd={<ArrowRight />} disabled={page >= lastPage} onClick={() => onSearch({ ...search, page: page + 1 })}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}

function Storage() {
  const { data, isPending, isError, refetch } = useMyUsage()
  if (isPending) return <Skeleton className="h-12 w-full" aria-label="Loading storage" />
  if (isError) return <Retry label="Couldn't load your storage." onRetry={() => refetch()} />
  return (
    <div className="space-y-2">
      <UsageMeter label="Your files, across all projects" used={data.bytes_used} limit={data.quota_bytes} format={formatBytes} />
      {data.by_project.length > 0 && <p className="text-xs text-muted-foreground">{data.by_project.map((x) => `${x.project_name} ${formatBytes(x.bytes)}`).join(" · ")}</p>}
    </div>
  )
}

export function AccountPage({ search, onSearch }: { search: AccountSearch; onSearch: (next: AccountSearch) => void }) {
  useDocumentTitle("Account · Pro-Goal")
  const { me } = useRouteContext({ from: "/app" })
  const handled = useRef(false)
  useEffect(() => {
    const result = slackReturn(search.slack, search.reason)
    if (!result || handled.current) return
    handled.current = true
    if (result.kind === "success") toast.success(result.text)
    else toast.error(result.text)
    onSearch({})
  }, [search, onSearch])
  return (
    <div className="space-y-8">
      <PageHeader title="Account" description="Your profile, sign-in and security, notifications and file storage." />
      {me.deletion_scheduled_for && <DeleteSection me={me} />}
      <Section id="profile" title="Profile" description="How you appear to teammates.">
        <ProfileSection me={me} />
      </Section>
      <Section id="sessions" title="Signed-in devices" description="Sign out any device you don't recognise. It stops working at once.">
        <Sessions />
      </Section>
      <Section id="password" title="Password" description="Changing it signs out every other device.">
        <PasswordSection />
      </Section>
      <Section id="email" title="Email" description="The address you sign in with and receive notices at.">
        <EmailSection email={me.email} />
      </Section>
      <Section id="log" title="Security log" description="Sign-ins, wrong passwords and account changes, kept for 180 days.">
        <SecurityLog search={search} onSearch={onSearch} />
      </Section>
      <Section id="slack" title="Slack" description="Link your Slack account to get direct messages and to run /task commands as yourself.">
        <SlackLinkSection />
      </Section>
      <Section id="notifications" title="Notifications" description="Choose how you hear about things that involve you. Everything else is posted to project channels.">
        <NotificationsSection />
      </Section>
      <Section id="storage" title="File storage" description="Files you uploaded count against your allowance in every project.">
        <Storage />
      </Section>
      {!me.deletion_scheduled_for && (
        <Section id="delete" title="Delete account" description="Starts a 7-day countdown you can cancel.">
          <DeleteSection me={me} />
        </Section>
      )}
    </div>
  )
}
