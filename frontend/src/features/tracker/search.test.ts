import { describe, expect, it } from "vitest"
import { activeFilterCount, toFilters, validateTaskSearch, withSearch } from "./search"

describe("task search", () => {
  it("drops junk and keeps valid values", () => {
    const s = validateTaskSearch({ status: " abc ", after: "2026-10-01", before: "nope", overdue: "true", sort: "evil", page: "3", q: "" })
    expect(s).toMatchObject({ status: "abc", after: "2026-10-01", before: undefined, overdue: true, sort: undefined, page: 3, q: undefined })
  })
  it("reads numeric-looking text and bounds the page", () => {
    expect(validateTaskSearch({ q: 123, tag: 2024, page: "99999" })).toMatchObject({ q: "123", tag: "2024", page: undefined })
  })
  it("sorts newest first by default", () => {
    expect(toFilters({}).ordering).toBe("-number")
    expect(toFilters({ sort: "title" }).ordering).toBe("title")
  })
  it("hides subtasks unless asked", () => {
    expect(toFilters({}).top_level).toBe(true)
    expect(toFilters({ subtasks: true }).top_level).toBeUndefined()
  })
  it("maps dates to backend filter names", () => {
    expect(toFilters({ after: "2026-10-01", before: "2026-10-31" })).toMatchObject({ due_date_after: "2026-10-01", due_date_before: "2026-10-31" })
  })
  it("counts filters but not sort or paging", () => {
    expect(activeFilterCount({ status: "a", q: "x", sort: "title", page: 2 })).toBe(2)
  })
  it("restarts paging when filters change", () => {
    expect(withSearch({ page: 4, status: "a" }, { status: "b" }).page).toBeUndefined()
  })
})
