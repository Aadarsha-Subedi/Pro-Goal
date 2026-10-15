import { createContext, useContext, useRef, useState } from "react"
import Markdown, { defaultUrlTransform, type Components } from "react-markdown"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Code, ImageSquare, ListBullets, TextB, TextItalic } from "@/icons"

/** Links leave the app in a new tab without the referrer. Images only come from project attachments (resolved by the caller); anything else is shown as its alt text, so no third-party host sees the viewer. */
type ImageResolver = (attachmentId: string, alt: string) => React.ReactNode
/** Where `attachment:<id>` images come from. Pages that own attachments provide one; without it they read as text. */
export const MarkdownImages = createContext<ImageResolver | null>(null)

function MdImage({ src, alt }: { src?: string; alt?: string }) {
  const resolve = useContext(MarkdownImages)
  const id = src?.startsWith("attachment:") ? src.slice("attachment:".length) : null
  if (id && resolve) return <>{resolve(id, alt ?? "")}</>
  return <span className="text-muted-foreground">[image{alt ? `: ${alt}` : ""}]</span>
}

const SAFE: Components = {
  a: ({ node: _n, ...p }) => <a {...p} target="_blank" rel="noopener noreferrer nofollow" />,
  img: ({ node: _n, src, alt }) => <MdImage src={typeof src === "string" ? src : undefined} alt={alt} />,
}

// `attachment:` is ours; every other scheme goes through react-markdown's own check (javascript: and friends are emptied).
const urlTransform = (url: string) => (url.startsWith("attachment:") ? url : defaultUrlTransform(url))

/** Rendered markdown. react-markdown ignores raw HTML and rewrites unsafe link protocols by default. */
export function MarkdownView({ source, empty }: { source: string; empty?: string }) {
  if (!source.trim()) return empty ? <p className="text-sm text-muted-foreground">{empty}</p> : null
  return (
    <div className="space-y-2 text-sm leading-relaxed [&_a]:text-primary [&_a]:underline [&_blockquote]:border-l [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:font-mono [&_code]:text-xs [&_h1]:text-lg [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-medium [&_ol]:ml-5 [&_ol]:list-decimal [&_pre]:overflow-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3 [&_ul]:ml-5 [&_ul]:list-disc">
      <Markdown components={SAFE} urlTransform={urlTransform}>{source}</Markdown>
    </div>
  )
}

type Wrap = { before: string; after?: string; label: string; Icon: typeof TextB }
const TOOLS: Wrap[] = [
  { before: "**", after: "**", label: "Bold", Icon: TextB },
  { before: "_", after: "_", label: "Italic", Icon: TextItalic },
  { before: "- ", label: "List", Icon: ListBullets },
  { before: "`", after: "`", label: "Code", Icon: Code },
]

interface EditorProps {
  defaultValue?: string
  /** Controlled value. Omit both to let the editor keep its own text. */
  value?: string
  onChange?: (value: string) => void
  disabled?: boolean
  label?: string
  minRows?: number
  autoFocus?: boolean
  /** Extra controls under the text area, e.g. a mention picker. */
  footer?: React.ReactNode
  /** When given, an Insert image button uploads the chosen file and writes the markdown for it. */
  imageUpload?: (file: File) => Promise<{ id: string; name: string }>
}

export function MarkdownEditor({ defaultValue = "", value: controlled, onChange, disabled, label = "Markdown", minRows = 6, autoFocus, footer, imageUpload }: EditorProps) {
  const picker = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [tab, setTab] = useState<"write" | "preview">("write")
  const [own, setOwn] = useState(defaultValue)
  const value = controlled ?? own
  const area = useRef<HTMLTextAreaElement>(null)
  const set = (v: string) => {
    if (controlled === undefined) setOwn(v)
    onChange?.(v)
  }
  // Toolbar buttons wrap the selection (or insert at the caret) and keep the caret where typing continues.
  const apply = ({ before, after = "" }: Wrap) => {
    const el = area.current
    if (!el) return
    const { selectionStart: a, selectionEnd: b } = el
    set(value.slice(0, a) + before + value.slice(a, b) + after + value.slice(b))
    requestAnimationFrame(() => {
      el.focus()
      el.setSelectionRange(a + before.length, b + before.length)
    })
  }
  const insertImage = async (file: File) => {
    if (!imageUpload) return
    setUploading(true)
    setUploadError(null)
    try {
      const { id, name } = await imageUpload(file)
      const el = area.current
      const at = el?.selectionStart ?? value.length
      set(`${value.slice(0, at)}${value && !value.slice(0, at).endsWith("\n") ? "\n" : ""}![${name.replace(/[[\]]/g, "")}](attachment:${id})\n${value.slice(at)}`)
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Couldn't upload the image.")
    } finally {
      setUploading(false)
    }
  }
  return (
    <div className="rounded-lg border">
      <div className="flex items-center gap-1 border-b px-2">
        <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
          <TabsList variant="line">
            <TabsTrigger value="write">Write</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="ml-auto flex">
          {imageUpload && <Button variant="ghost" size="icon-sm" label="Insert image" loading={uploading} disabled={disabled || tab !== "write"} onClick={() => picker.current?.click()}><ImageSquare /></Button>}
          {TOOLS.map((t) => (
            <Button key={t.label} variant="ghost" size="icon-sm" label={t.label} disabled={disabled || tab !== "write"} onClick={() => apply(t)}><t.Icon /></Button>
          ))}
        </div>
      </div>
      <div className="p-3">
        {tab === "write" ? (
          <Textarea ref={area} aria-label={label} value={value} disabled={disabled} autoFocus={autoFocus} rows={minRows} onChange={(e) => set(e.target.value)} className="min-h-24 border-0 p-0 font-mono text-xs shadow-none focus-visible:ring-0" />
        ) : (
          <MarkdownView source={value} empty="Nothing to preview yet." />
        )}
      </div>
      {imageUpload && <input ref={picker} type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden tabIndex={-1} onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) void insertImage(f) }} />}
      {uploadError && <p role="alert" className="border-t px-3 py-2 text-xs text-destructive">{uploadError}</p>}
      {footer && <div className="border-t px-3 py-2">{footer}</div>}
    </div>
  )
}
