import { ApiError } from "@/lib/api"
import { projectError } from "@/features/projects/errors"
import { UploadError } from "./api"

const MESSAGES: Record<string, string> = {
  attachments_not_configured: "File storage isn't set up on this server yet.",
  attachment_not_found: "This file no longer exists.",
  attachment_target_not_found: "The item you are attaching to no longer exists.",
  attachment_target_required: "Choose what to attach the file to.",
  file_type_not_allowed: "That file type isn't allowed. Images, PDF, Word, Excel, PowerPoint, text and MP3 or M4A audio only.",
  file_too_large: "That file is too large.",
  empty_file: "That file is empty.",
  user_quota_exceeded: "You've used your 100 MB of file storage. Delete some of your files to upload more.",
  project_quota_exceeded: "This project is out of file storage. Delete files to make room.",
  attachment_target_full: "This item already has 20 files. Delete one to add another.",
  attachment_not_pending: "This upload already finished.",
  upload_missing: "The upload didn't arrive. Try again.",
  upload_size_mismatch: "The upload was cut short. Try again.",
  attachment_not_ready: "This file is still being processed. Try again in a moment.",
  invalid_note_image: "Images in notes must be files attached to this project.",
}

export function attachmentError(err: unknown): string {
  if (err instanceof UploadError) {
    if (err.code === "storage_unreachable") return "Couldn't reach file storage. Check your connection, and that the storage bucket allows this site (CORS), then try again."
    if (err.code === "storage_rejected") return "Storage refused the upload. It may have expired. Try again."
    return "Upload cancelled."
  }
  if (err instanceof ApiError && MESSAGES[err.code]) return err.code === "file_too_large" && err.message ? err.message : MESSAGES[err.code]
  return projectError(err)
}
