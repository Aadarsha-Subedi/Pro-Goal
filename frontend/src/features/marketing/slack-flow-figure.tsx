import { useGSAP } from "@gsap/react"
import { useRef } from "react"
import { StatusLabel } from "@/components/patterns/status"
import { SlackMark } from "@/components/patterns/slack-mark"
import { Target } from "@/icons"
import { EASE, gsap, reducedMotion } from "@/motion"

const MESSAGES = [
  { time: "10:02", text: "Dev moved PM-142 Fix login redirect to In progress." },
  { time: "10:09", text: "Sam commented on PM-142: Redirect fixed on staging." },
  { time: "10:15", text: "PM-142 Fix login redirect is done." },
]

/** Figure 1: a task changes in the app and the Slack channel hears about it, in order. Static final state under reduced motion. */
export function SlackFlowFigure() {
  const ref = useRef<HTMLElement>(null)
  useGSAP(
    () => {
      if (reducedMotion()) return
      const q = gsap.utils.selector(ref)
      const msgs = q("[data-msg]")
      const [todo, progress, done] = [q("[data-s=todo]"), q("[data-s=progress]"), q("[data-s=done]")]
      gsap.set([progress, done], { opacity: 0 })
      gsap.set(todo, { opacity: 1 })
      gsap.set(msgs, { opacity: 0, y: 10 })
      const show = { opacity: 1, y: 0, duration: 0.6 }
      const tl = gsap.timeline({
        repeat: -1,
        defaults: { ease: EASE },
        scrollTrigger: { trigger: ref.current, start: "top bottom", toggleActions: "play pause resume pause" },
      })
      tl.to(todo, { opacity: 0, duration: 0.3 }, 0.9)
        .to(progress, { opacity: 1, duration: 0.3 }, 0.9)
        .to(msgs[0], show, 1.2)
        .to(msgs[1], show, 3.2)
        .to(progress, { opacity: 0, duration: 0.3 }, 5.4)
        .to(done, { opacity: 1, duration: 0.3 }, 5.4)
        .to(msgs[2], show, 5.7)
        .to(msgs, { opacity: 0, duration: 0.5, ease: "power1.in" }, 9.4)
        .to(done, { opacity: 0, duration: 0.3 }, 9.6)
        .to(todo, { opacity: 1, duration: 0.3 }, 9.6)
        .to({}, { duration: 0.6 })
    },
    { scope: ref },
  )
  return (
    <figure ref={ref} aria-labelledby="fig1">
      <div className="bp-block">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-4 text-sm">
          <span className="bp-mono bp-muted">PM-142</span>
          <span className="min-w-0 flex-1 basis-48 font-medium">Fix login redirect after email verification</span>
          <span className="grid">
            <span data-s="todo" aria-hidden className="col-start-1 row-start-1"><StatusLabel status="todo" /></span>
            <span data-s="progress" aria-hidden className="col-start-1 row-start-1"><StatusLabel status="progress" /></span>
            <span data-s="done" className="col-start-1 row-start-1"><StatusLabel status="done" /></span>
          </span>
        </div>
        <div className="px-4 py-4">
          <div className="flex items-center gap-3">
            <SlackMark className="size-9 shrink-0" />
            <div>
              <p className="text-sm leading-tight font-semibold">Slack</p>
              <p className="bp-mono text-xs bp-muted"># apollo-dev</p>
            </div>
          </div>
          <ul className="mt-4 space-y-3">
            {MESSAGES.map((m) => (
              <li key={m.time} data-msg className="flex gap-3">
                <span className="grid size-8 shrink-0 place-items-center rounded-sm bg-primary text-primary-foreground" aria-hidden><Target weight="fill" className="size-5" /></span>
                <div className="min-w-0 text-sm">
                  <p className="leading-tight"><span className="font-semibold">Pro-Goal</span> <span className="bp-mono ml-1 text-xs bp-muted">{m.time}</span></p>
                  <p className="mt-0.5">{m.text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <figcaption id="fig1" className="bp-mono mt-2 text-xs bp-muted">FIG. 1 — A task changes in Pro-Goal. The Slack channel hears about it.</figcaption>
    </figure>
  )
}
