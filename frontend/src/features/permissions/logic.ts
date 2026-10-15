import type { Preset, Registry } from "@/features/projects/api"

export interface Held {
  role: string
  permissions: string[]
}

/** The owner holds every registered code; others hold their grants. Mirrors the backend subset rule. */
export function holds(actor: Held, registry: Registry, code: string): boolean {
  return actor.role === "owner" ? registry.permissions.some((p) => p.code === code) : actor.permissions.includes(code)
}

export function diffGrants(current: readonly string[], wanted: readonly string[]): { added: string[]; removed: string[] } {
  const have = new Set(current)
  const want = new Set(wanted)
  return {
    added: [...want].filter((c) => !have.has(c)).sort(),
    removed: [...have].filter((c) => !want.has(c)).sort(),
  }
}

/** The preset whose codes equal the grants exactly, else null (shown as "Custom"). */
export function presetFor(codes: readonly string[], presets: readonly Preset[]): Preset | null {
  const set = new Set(codes)
  return presets.find((p) => p.permissions.length === set.size && p.permissions.every((c) => set.has(c))) ?? null
}

/** Apply a preset to a draft. Codes the actor does not hold keep their current state, since the server would refuse changing them. */
export function applyPreset(draft: readonly string[], preset: Preset, canChange: (code: string) => boolean, registry: Registry): string[] {
  const next = new Set<string>()
  for (const { code } of registry.permissions) {
    const wanted = preset.permissions.includes(code)
    if (canChange(code) ? wanted : draft.includes(code)) next.add(code)
  }
  return [...next]
}

export function toggle(draft: readonly string[], code: string, on: boolean): string[] {
  const rest = draft.filter((c) => c !== code)
  return on ? [...rest, code] : rest
}

export interface GroupCount {
  group: string
  held: number
  total: number
}

export function groupCounts(codes: readonly string[], registry: Registry): GroupCount[] {
  const set = new Set(codes)
  return registry.groups.map((group) => {
    const inGroup = registry.permissions.filter((p) => p.group === group)
    return { group, total: inGroup.length, held: inGroup.filter((p) => set.has(p.code)).length }
  })
}

export type CellState = "all" | "some" | "none"
export function cellState({ held, total }: { held: number; total: number }): CellState {
  return held === 0 ? "none" : held === total ? "all" : "some"
}
