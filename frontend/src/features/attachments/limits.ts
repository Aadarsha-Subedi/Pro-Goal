/** Mirrors backend/attachments/constants/types.py so most refusals never leave the browser. The server stays the authority. */
export type Category = "image" | "document" | "audio"

const MB = 1024 * 1024

export const CATEGORY_MAX: Record<Category, number> = { image: 5 * MB, document: 10 * MB, audio: 20 * MB }
export const MAX_PER_TARGET = 20

const TYPES: Record<string, Category> = {
  "image/jpeg": "image",
  "image/png": "image",
  "image/webp": "image",
  "image/gif": "image",
  "application/pdf": "document",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "document",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": "document",
  "text/plain": "document",
  "audio/mpeg": "audio",
  "audio/mp4": "audio",
  "audio/x-m4a": "audio",
}

const BY_EXTENSION: Record<string, string> = {
  jpg: "image/jpeg", jpeg: "image/jpeg", png: "image/png", webp: "image/webp", gif: "image/gif",
  pdf: "application/pdf", txt: "text/plain", mp3: "audio/mpeg", m4a: "audio/mp4",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

/** The type to declare: the browser's, or one inferred from the extension when the browser leaves it empty. */
export function declaredType(file: { name: string; type: string }): string {
  const t = file.type.split(";")[0].trim().toLowerCase()
  if (t) return t
  const ext = file.name.split(".").pop()?.toLowerCase() ?? ""
  return BY_EXTENSION[ext] ?? ""
}

export type CheckResult = { ok: true; type: string; category: Category } | { ok: false; reason: string }

export function checkFile(file: { name: string; type: string; size: number }): CheckResult {
  const type = declaredType(file)
  const category = TYPES[type]
  if (!category) return { ok: false, reason: `${file.name} isn't an allowed file type. Images, PDF, Word, Excel, PowerPoint, text and MP3 or M4A audio only.` }
  if (file.size <= 0) return { ok: false, reason: `${file.name} is empty.` }
  if (file.size > CATEGORY_MAX[category]) return { ok: false, reason: `${file.name} is larger than ${CATEGORY_MAX[category] / MB} MB, the limit for ${category === "audio" ? "audio" : category === "image" ? "images" : "documents"}.` }
  return { ok: true, type, category }
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n >= 1024 * MB) return `${(n / (1024 * MB)).toFixed(n < 10 * 1024 * MB ? 1 : 0).replace(/\.0$/, "")} GB`
  if (n < MB) return `${(n / 1024).toFixed(n < 10 * 1024 ? 1 : 0)} KB`
  return `${(n / MB).toFixed(n < 10 * MB ? 1 : 0)} MB`
}
