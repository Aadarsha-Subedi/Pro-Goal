import type { LazyOptions } from "@/lib/lazy-options"

/** What a dropdown shows in place of choices while they load or when loading failed. Renders nothing otherwise. */
export function OptionsState({ source, empty }: { source: Pick<LazyOptions<unknown>, "loading" | "error" | "retry" | "items">; empty?: string }) {
  if (source.loading) return <p role="status" className="px-2 py-1.5 text-sm text-muted-foreground">Loading…</p>
  if (source.error)
    return (
      <p role="alert" className="flex items-center gap-2 px-2 py-1.5 text-sm text-destructive">
        Couldn't load.
        <button type="button" onClick={source.retry} className="rounded-sm underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-ring">Try again</button>
      </p>
    )
  if (empty && source.items.length === 0) return <p className="px-2 py-1.5 text-sm text-muted-foreground">{empty}</p>
  return null
}
