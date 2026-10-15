import { eventInfo } from "@/features/integrations/events"
import { SlackMark } from "@/components/patterns/slack-mark"

const MAPPINGS = [
  { channel: "apollo-dev", project: "Apollo", events: ["task_created", "task_assigned", "comment_added", "task_overdue"] },
  { channel: "apollo-owners", project: "Apollo", events: ["join_request_created", "member_joined"] },
]

/** Figure 3: which Slack channel gets which events for a project. */
export function SlackMappingFigure() {
  return (
    <figure aria-labelledby="fig3">
      <div className="flex items-center gap-3 border-y bp-rule-strong py-3">
        <SlackMark className="size-9 shrink-0" />
        <div>
          <p className="text-sm leading-tight font-semibold">Slack workspace connected</p>
          <p className="text-sm bp-muted">One channel per purpose. You choose the events.</p>
        </div>
      </div>
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">Slack channels mapped to events in the Apollo project</caption>
        <thead>
          <tr className="border-b bp-rule-strong text-left">
            <th scope="col" className="bp-cell-label h-9 w-40 px-3 font-medium">Channel</th>
            <th scope="col" className="bp-cell-label h-9 px-3 font-medium">Posts when</th>
          </tr>
        </thead>
        <tbody>
          {MAPPINGS.map((m) => (
            <tr key={m.channel} className="border-b bp-rule align-top">
              <th scope="row" className="bp-mono px-3 py-3 text-left font-medium"># {m.channel}</th>
              <td className="px-3 py-3">
                <ul className="flex flex-wrap gap-x-4 gap-y-1">
                  {m.events.map((e) => {
                    const { label, icon: Icon } = eventInfo(e)
                    return <li key={e} className="inline-flex items-center gap-1.5"><Icon className="size-4 bp-muted" aria-hidden />{label}</li>
                  })}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <figcaption id="fig3" className="bp-mono mt-2 text-xs bp-muted">FIG. 3 — Two channels in one project, each with its own events.</figcaption>
    </figure>
  )
}
