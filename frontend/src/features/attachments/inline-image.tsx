import { ImageSquare } from "@/icons"
import { useDownloadUrl } from "./queries"

/** An image written into a note as `![alt](attachment:id)`, resolved to a short-lived signed link. */
export function InlineImage({ projectId, id, alt }: { projectId: string; id: string; alt: string }) {
  const { data, isPending, isError } = useDownloadUrl(projectId, id, true)
  if (isPending) return <span className="inline-block h-24 w-40 animate-pulse rounded-md bg-muted" role="img" aria-label="Loading image" />
  if (isError || !data) return <span className="inline-flex items-center gap-1.5 text-muted-foreground"><ImageSquare className="size-4" aria-hidden />Image unavailable{alt ? `: ${alt}` : ""}</span>
  return <img src={data.url} alt={alt} loading="lazy" referrerPolicy="no-referrer" className="my-2 max-h-96 max-w-full rounded-md border" />
}
