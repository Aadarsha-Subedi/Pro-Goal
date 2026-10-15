import { describe, expect, it } from "vitest"
import { renderMentions, toDisplay, toWire } from "./mentions"

const id1 = "01a12517-d745-7665-bc0f-305de87f366c"
const id2 = "01a12517-d745-7665-bc0f-305de87f3670"
const byId = new Map([[id1, { name: "Ann" }], [id2, { name: "Anna" }]])

describe("mentions", () => {
  it("turns tokens into names and back", () => {
    const wire = `hi @[user:${id1}] and @[user:${id2}]`
    const { text, mentions } = toDisplay(wire, byId)
    expect(text).toBe("hi @Ann and @Anna")
    expect(toWire(text, mentions)).toBe(wire)
  })
  it("does not let a short name swallow a longer one", () => {
    expect(toWire("@Anna and @Ann", [{ id: id1, name: "Ann" }, { id: id2, name: "Anna" }])).toBe(`@[user:${id2}] and @[user:${id1}]`)
  })
  it("names people who left", () => {
    expect(toDisplay(`@[user:${id1}]`, new Map()).text).toBe("@someone")
    expect(renderMentions(`@[user:${id1}]`, byId)).toBe("**@Ann**")
  })
  it("leaves plain @text alone", () => {
    expect(toWire("email me @home", [])).toBe("email me @home")
  })
})

describe("markdown safety", () => {
  it("escapes a name that looks like markdown", async () => {
    const { escapeMd } = await import("./mentions")
    expect(escapeMd("](https://x)")).toBe("\\]\\(https://x\\)")
    expect(renderMentions(`@[user:${id1}]`, new Map([[id1, { name: "a*b_c" }]]))).toBe("**@a\\*b\\_c**")
  })
})
