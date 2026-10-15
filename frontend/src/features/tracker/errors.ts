import { ApiError } from "@/lib/api"
import { projectError } from "@/features/projects/errors"

/** Plain-language message per tracker error code. Falls back to the project messages, then a generic line. */
const MESSAGES: Record<string, string> = {
  task_not_found: "This task doesn't exist or was deleted.",
  task_not_deleted: "This task isn't deleted.",
  task_restore_window_over: "The 7-day restore window is over.",
  invalid_date_range: "The due date can't be before the start date.",
  subtask_of_subtask: "Subtasks can't have subtasks. Choose a top-level task as the parent.",
  task_has_subtasks: "This task has subtasks, so it can't become a subtask. Move or delete them first.",
  invalid_parent: "That task can't be the parent.",
  open_subtasks: "Finish or move the open subtasks before closing this task.",
  assignee_not_member: "Only project members can be assigned.",
  status_not_found: "That status no longer exists. Reload and try again.",
  priority_not_found: "That priority no longer exists. Reload and try again.",
  duplicate_name: "Another item already uses that name.",
  last_in_category: "Each group needs at least one status. Add another in this group first.",
  in_use_needs_replacement: "Tasks still use this. Choose where to move them.",
  invalid_replacement: "Choose a different item to move the tasks to.",
  cannot_delete_default: "The default can't be deleted. Make another item the default first.",
  note_not_found: "This note doesn't exist or was deleted.",
  note_too_large: "This note is too large. Shorten it and save again.",
  stale_data: "Someone else changed this note while you were editing.",
  comment_not_found: "This comment no longer exists.",
  comment_deleted: "This comment was deleted.",
  invalid_note_image: "Images in notes must be files uploaded to this project.",
  invalid_sort: "That sort isn't available.",
}

export function trackerError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "fields_forbidden") {
      const fields = err.errors.map((e) => e.field).filter(Boolean)
      return fields.length > 0 ? `You can't change: ${fields.join(", ")}. Nothing was saved.` : "You don't have permission to change that. Nothing was saved."
    }
    if (MESSAGES[err.code]) return MESSAGES[err.code]
    // Field problems come with their own plain sentence.
    if (err.code === "validation_error" && err.errors[0]?.message) return err.errors[0].message
  }
  return projectError(err)
}

export function isStale(err: unknown): boolean {
  return err instanceof ApiError && err.code === "stale_data"
}
