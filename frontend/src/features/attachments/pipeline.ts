import { attachmentsApi, putToStorage, type Attachment, type Target, type UploadTicket } from "./api"
import { attachmentError } from "./errors"
import { checkFile } from "./limits"

export type UploadPhase = "uploading" | "confirming" | "processing" | "done" | "failed" | "cancelled"

export interface UploadState {
  id: string
  name: string
  size: number
  phase: UploadPhase
  /** 0 to 1 while uploading. */
  progress: number
  error?: string
  attachment?: Attachment
}

export interface Deps {
  requestUpload: (projectId: string, target: Target, file: { name: string; size: number }, type: string) => Promise<UploadTicket>
  put: (ticket: UploadTicket["upload"], file: Blob, onProgress: (f: number) => void, signal?: AbortSignal) => Promise<void>
  confirm: (projectId: string, id: string) => Promise<Attachment>
  get: (projectId: string, target: Target, id: string) => Promise<Attachment>
  wait: (ms: number) => Promise<void>
}

export const realDeps: Deps = {
  requestUpload: attachmentsApi.requestUpload,
  put: putToStorage,
  confirm: attachmentsApi.confirm,
  get: attachmentsApi.get,
  wait: (ms) => new Promise((r) => setTimeout(r, ms)),
}

/** How many times an image still being re-encoded is checked, and how far apart. */
export const POLL = { tries: 20, ms: 1000 }

/** One file, start to finish. Reports each step through `emit`; never throws. */
export async function runUpload(projectId: string, target: Target, file: File, id: string, emit: (s: UploadState) => void, signal: AbortSignal, deps: Deps = realDeps): Promise<void> {
  const base = { id, name: file.name, size: file.size }
  const fail = (e: unknown) => emit({ ...base, phase: signal.aborted ? "cancelled" : "failed", progress: 0, error: signal.aborted ? undefined : attachmentError(e) })
  const checked = checkFile(file)
  if (!checked.ok) return emit({ ...base, phase: "failed", progress: 0, error: checked.reason })
  try {
    const ticket = await deps.requestUpload(projectId, target, file, checked.type)
    emit({ ...base, phase: "uploading", progress: 0, attachment: ticket.attachment })
    await deps.put(ticket.upload, file, (progress) => emit({ ...base, phase: "uploading", progress, attachment: ticket.attachment }), signal)
    emit({ ...base, phase: "confirming", progress: 1, attachment: ticket.attachment })
    let attachment = await deps.confirm(projectId, ticket.attachment.id)
    for (let i = 0; attachment.status !== "ready" && i < POLL.tries; i++) {
      emit({ ...base, phase: "processing", progress: 1, attachment })
      if (signal.aborted) return emit({ ...base, phase: "cancelled", progress: 1, attachment })
      await deps.wait(POLL.ms)
      attachment = await deps.get(projectId, target, attachment.id)
    }
    emit({ ...base, phase: "done", progress: 1, attachment })
  } catch (e) {
    fail(e)
  }
}
