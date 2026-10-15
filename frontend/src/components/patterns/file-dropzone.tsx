import { useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { File as FileIcon, Lock, UploadSimple } from "@/icons"
import { cn } from "@/lib/utils"

/**
 * Drop target plus a keyboard-reachable Browse button. Pasting files works while it has focus.
 * It only hands files over (`onFiles`); what happens next is the caller's. When off, the reason is written inside it.
 */
export function FileDropzone({ onFiles, disabledReason, hint = "Images, PDF, Word, Excel, PowerPoint, text and audio. Up to 5 MB for images, 10 MB for documents, 20 MB for audio.", compact }: { onFiles: (files: File[]) => void; disabledReason?: string; hint?: string; compact?: boolean }) {
  const [over, setOver] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const off = !!disabledReason
  const take = (list: FileList | null) => {
    const files = list ? Array.from(list) : []
    if (files.length > 0 && !off) onFiles(files)
  }
  return (
    <div
      tabIndex={off ? -1 : 0}
      onDragOver={(e) => { e.preventDefault(); if (!off) setOver(true) }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); take(e.dataTransfer.files) }}
      onPaste={(e) => take(e.clipboardData.files)}
      className={cn("flex flex-col items-center gap-2 rounded-lg border border-dashed text-center outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50", compact ? "px-4 py-4" : "px-6 py-8", over && "border-primary bg-accent", off && "opacity-70")}
    >
      {off ? <Lock className="size-5 text-muted-foreground" aria-hidden /> : <UploadSimple className="size-5 text-muted-foreground" weight="duotone" aria-hidden />}
      <p className="text-sm">{off ? disabledReason : "Drop files here, paste, or"}</p>
      {!off && <Button variant="outline" size="sm" icon={<FileIcon />} onClick={() => input.current?.click()}>Browse files</Button>}
      {!off && <p className="max-w-md text-xs text-muted-foreground">{hint}</p>}
      <input ref={input} type="file" multiple hidden tabIndex={-1} onChange={(e) => { take(e.target.files); e.target.value = "" }} />
    </div>
  )
}
