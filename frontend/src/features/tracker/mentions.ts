/** Mentions travel as `@[user:<uuid>]`; people read and type `@Name`. */
const TOKEN = /@\[user:([0-9a-fA-F-]{36})\]/g

export interface Mention {
  id: string
  name: string
}

/** Wire text to display text. Unknown people (left the project) read as "@someone". */
export function toDisplay(body: string, byId: Map<string, { name: string }>): { text: string; mentions: Mention[] } {
  const mentions: Mention[] = []
  const text = body.replace(TOKEN, (_m, id: string) => {
    const name = byId.get(id)?.name ?? "someone"
    if (!mentions.some((m) => m.id === id)) mentions.push({ id, name })
    return `@${name}`
  })
  return { text, mentions }
}

/** Display text to wire text: each `@Name` that was picked becomes its token. Longest names first so "Ann" doesn't eat "Anna". */
export function toWire(text: string, mentions: Mention[]): string {
  let out = text
  for (const m of [...mentions].sort((a, b) => b.name.length - a.name.length)) {
    out = out.split(`@${m.name}`).join(`@[user:${m.id}]`)
  }
  return out
}

/** A member's name must never turn into markdown (links, images, emphasis). */
export const escapeMd = (s: string) => s.replace(/[\\`*_{}[\]()#+\-.!|<>~]/g, "\\$&")

/** For rendering: tokens become bold names. */
export function renderMentions(body: string, byId: Map<string, { name: string }>): string {
  return body.replace(TOKEN, (_m, id: string) => `**@${escapeMd(byId.get(id)?.name ?? "someone")}**`)
}
