import { useGSAP } from "@gsap/react"
import { useRef } from "react"
import { EASE, gsap, reducedMotion } from "@/motion"

const REVS = [
  { rev: "A", text: "Join request: Liam Novak, code K7P2QX", by: "Liam", note: "signed" },
  { rev: "B", text: "Approved as Member", by: "Maya (owner)", note: "signed" },
  { rev: "C", text: "Granted: change status, edit notes", by: "Maya (owner)", note: "signed" },
]

function SignBox({ signed }: { signed: boolean }) {
  return (
    <span className="inline-grid size-6 place-items-center border bp-rule-strong">
      {signed && (
        <svg className="bp-sign size-4 text-success" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M3 8.5l3.2 3.2L13 4.8" />
        </svg>
      )}
    </span>
  )
}

/** Revision table: each row is signed in turn when it scrolls into view. */
export function RevisionTable() {
  const ref = useRef<HTMLTableElement>(null)
  useGSAP(
    () => {
      if (reducedMotion()) return
      const boxes = gsap.utils.toArray<SVGElement>(".bp-sign", ref.current).filter((b) => b.getBoundingClientRect().top > window.innerHeight * 0.85)
      if (boxes.length === 0) return
      boxes.forEach((b) => b.classList.add("is-armed"))
      const tl = gsap.timeline({ scrollTrigger: { trigger: ref.current, start: "top 85%", once: true } })
      boxes.forEach((b, i) => tl.add(() => b.classList.remove("is-armed"), i * 0.7 + 0.2))
      tl.to({}, { duration: 0.1, ease: EASE })
    },
    { scope: ref },
  )
  return (
    <table ref={ref} className="w-full border-collapse text-sm">
      <caption className="sr-only">Revision history of a join request. Each revision is signed by the person who made it.</caption>
      <thead>
        <tr className="border-y bp-rule-strong text-left">
          <th scope="col" className="bp-cell-label h-9 w-12 px-3 font-medium">Rev</th>
          <th scope="col" className="bp-cell-label h-9 px-3 font-medium">Description</th>
          <th scope="col" className="bp-cell-label hidden h-9 px-3 font-medium sm:table-cell">By</th>
          <th scope="col" className="bp-cell-label h-9 w-24 px-3 text-center font-medium">Signed</th>
        </tr>
      </thead>
      <tbody>
        {REVS.map((r) => (
          <tr key={r.rev} className="border-b bp-rule">
            <th scope="row" className="bp-mono h-12 px-3 text-left font-medium">{r.rev}</th>
            <td className="px-3">{r.text}</td>
            <td className="hidden px-3 bp-muted sm:table-cell">{r.by}</td>
            <td className="px-3 text-center"><SignBox signed={r.note === "signed"} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
