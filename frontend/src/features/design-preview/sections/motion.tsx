import { useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { ArrowsClockwise, Lightning } from "@/icons"
import { CountUp, EASE, gsap, reducedMotion, useGSAP } from "@/motion"
import { Section, Specimen } from "../section"

export function MotionSection() {
  const [n, setN] = useState(1284)
  const stage = useRef<HTMLDivElement>(null)
  const { contextSafe } = useGSAP({ scope: stage })

  const play = contextSafe(() => {
    if (reducedMotion()) return
    gsap.fromTo("[data-stagger]", { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.7, ease: EASE, stagger: 0.06 })
  })

  return (
    <Section id="motion" title="Motion" intro="CSS handles hover and open states. GSAP handles orchestrated moments: scroll reveals (this whole page), list stagger, number tweens and layout flips. All of it switches off under reduced motion.">
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="List stagger">
          <div ref={stage}>
            <Button variant="outline" size="sm" icon={<ArrowsClockwise />} onClick={play} className="mb-3">Replay</Button>
            <ul className="divide-y rounded-lg border">
              {["Triage new requests", "Review join requests", "Plan next sprint", "Archive finished work"].map((l) => (
                <li key={l} data-stagger className="px-4 py-2.5 text-sm">{l}</li>
              ))}
            </ul>
          </div>
        </Specimen>
        <Specimen title="Number tween">
          <div className="flex items-center gap-4">
            <p className="text-3xl font-semibold tabular-nums"><CountUp value={n} /></p>
            <Button variant="outline" size="sm" icon={<Lightning />} onClick={() => setN(Math.round(500 + Math.random() * 9000))}>Update</Button>
            <span className="text-sm text-muted-foreground">tasks closed</span>
          </div>
        </Specimen>
      </div>
    </Section>
  )
}
