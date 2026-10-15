import { ApiError, api, type Page } from "@/lib/api"
import type { PublicUser } from "@/features/projects/api"
import type { Category } from "./limits"

export type AttachmentStatus = "pending" | "processing" | "ready"
export type TargetType = "task" | "note" | "comment"

export interface Attachment {
  id: string
  filename: string
  content_type: string
  category: Category
  size_bytes: number
  status: AttachmentStatus
  target: { type: TargetType; id: string }
  uploaded_by: PublicUser
  created_at: string
}

export interface UploadTicket {
  attachment: Attachment
  upload: { method: "PUT"; url: string; headers: Record<string, string>; expires_at: string }
}

export interface ProjectUsage {
  bytes_used: number
  quota_bytes: number
  by_category: Partial<Record<Category, number>>
  by_uploader: { user_id: string | null; first_name: string; bytes: number }[]
}

export interface MyUsage {
  bytes_used: number
  quota_bytes: number
  by_project: { project_id: string; project_name: string; bytes: number }[]
}

const P = (id: string) => `/api/projects/${id}`

export type Target = { type: "task"; id: number } | { type: "note" | "comment"; id: string }

const listQuery = (t: Target) => `${t.type}=${encodeURIComponent(String(t.id))}`

export const attachmentsApi = {
  list: (projectId: string, target: Target) => api.page<Attachment>(`${P(projectId)}/attachments/?${listQuery(target)}&limit=100`),
  requestUpload: (projectId: string, target: Target, file: { name: string; size: number }, contentType: string) =>
    api.post<UploadTicket>(`${P(projectId)}/attachments/upload-url/`, { target_type: target.type, target: String(target.id), filename: file.name, content_type: contentType, size: file.size }),
  confirm: (projectId: string, id: string) => api.post<Attachment>(`${P(projectId)}/attachments/${id}/confirm/`, {}),
  /** The backend has no single-file GET, so a file is looked up in its target's list (processing ones are listed too). */
  get: async (projectId: string, target: Target, id: string): Promise<Attachment> => {
    const found = (await attachmentsApi.list(projectId, target)).items.find((a) => a.id === id)
    if (!found) throw new ApiError(404, "attachment_not_found", "Attachment not found.")
    return found
  },
  download: (projectId: string, id: string) => api.get<{ url: string; expires_at: string }>(`${P(projectId)}/attachments/${id}/download/`),
  remove: (projectId: string, id: string) => api.delete<unknown>(`${P(projectId)}/attachments/${id}/`),
  projectUsage: (projectId: string) => api.get<ProjectUsage>(`${P(projectId)}/storage/`),
  myUsage: () => api.get<MyUsage>("/api/me/storage/"),
}

export type { Page }

/**
 * Sends the bytes straight to storage with exactly the headers the server signed. XMLHttpRequest, not fetch,
 * because only it reports upload progress. The session cookie and CSRF token are never sent to the storage host.
 */
export function putToStorage(ticket: UploadTicket["upload"], file: Blob, onProgress: (fraction: number) => void, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open(ticket.method, ticket.url)
    for (const [k, v] of Object.entries(ticket.headers)) xhr.setRequestHeader(k, v)
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total)
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new UploadError("storage_rejected", xhr.status)))
    xhr.onerror = () => reject(new UploadError("storage_unreachable", 0))
    xhr.onabort = () => reject(new UploadError("cancelled", 0))
    signal?.addEventListener("abort", () => xhr.abort(), { once: true })
    xhr.send(file)
  })
}

export class UploadError extends Error {
  code: "storage_rejected" | "storage_unreachable" | "cancelled"
  status: number
  constructor(code: UploadError["code"], status: number) {
    super(code)
    this.code = code
    this.status = status
  }
}
