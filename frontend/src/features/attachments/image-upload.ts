import type { Target } from "./api"
import { runUpload, type UploadState } from "./pipeline"

/** Uploads one image for the editor and resolves with its attachment id once it is ready. */
export function uploadImage(projectId: string, target: Target, file: File): Promise<{ id: string; name: string }> {
  return new Promise((resolve, reject) => {
    const ac = new AbortController()
    void runUpload(projectId, target, file, crypto.randomUUID(), (s: UploadState) => {
      if (s.phase === "done" && s.attachment) resolve({ id: s.attachment.id, name: s.attachment.filename })
      else if (s.phase === "failed") reject(new Error(s.error ?? "Couldn't upload the image."))
      else if (s.phase === "cancelled") reject(new Error("Upload cancelled."))
    }, ac.signal)
  })
}
