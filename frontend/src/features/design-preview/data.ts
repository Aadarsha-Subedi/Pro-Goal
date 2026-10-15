import type { TaskPriority, TaskStatus } from "@/components/patterns/status"

export interface Task {
  id: string
  number: number
  title: string
  status: TaskStatus
  priority: TaskPriority
  assignee: string
  due: string
  tags: string[]
}

export const TASKS: Task[] = [
  { id: "1", number: 142, title: "Fix login redirect after email verification", status: "progress", priority: "urgent", assignee: "Maya Chen", due: "Oct 12", tags: ["auth"] },
  { id: "2", number: 141, title: "Add rate limit headers to public endpoints", status: "todo", priority: "high", assignee: "Dev Patel", due: "Oct 14", tags: ["api"] },
  { id: "3", number: 139, title: "Kanban: sort columns by due date", status: "todo", priority: "medium", assignee: "Maya Chen", due: "Oct 15", tags: ["tracker"] },
  { id: "4", number: 137, title: "Slack digest message wording", status: "backlog", priority: "low", assignee: "Sam Rivera", due: "Oct 20", tags: ["slack"] },
  { id: "5", number: 134, title: "Quota warning when uploads near limit", status: "progress", priority: "high", assignee: "Dev Patel", due: "Oct 13", tags: ["files"] },
  { id: "6", number: 130, title: "Owner transfer re-auth flow", status: "done", priority: "medium", assignee: "Sam Rivera", due: "Oct 9", tags: ["projects", "auth"] },
  { id: "7", number: 128, title: "Explore page empty state", status: "done", priority: "low", assignee: "Maya Chen", due: "Oct 8", tags: ["explore"] },
  { id: "8", number: 125, title: "Retire old webhook secret", status: "cancelled", priority: "low", assignee: "Dev Patel", due: "Oct 7", tags: ["slack"] },
]
