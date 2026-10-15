import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { CheckCircle, Info, Plus, Warning, XCircle } from "@/icons"
import { Section, Specimen } from "../section"

const STEPS = [0.97, 0.93, 0.87, 0.8, 0.72, 0.62, 0.52, 0.42, 0.32]

function Scale() {
  return (
    <div className="flex overflow-hidden rounded-md">
      {STEPS.map((l) => (
        <div key={l} className="h-8 flex-1" style={{ background: `oklch(${l} calc(var(--accent-c) * ${l < 0.9 ? 1 : 0.25}) var(--h))` }} />
      ))}
    </div>
  )
}

const NEUTRALS = ["background", "surface", "muted", "secondary", "border", "muted-foreground", "foreground"]
const SWATCH_NAME: Record<string, string> = { background: "page", "muted-foreground": "soft text", foreground: "text" }
const SWATCH_LABEL: Record<string, string> = { "muted-foreground": "text-background", foreground: "text-background" }
const STATUS_ROWS = [
  { name: "Success", Icon: CheckCircle, tone: "text-success", text: "text-success-text" },
  { name: "Warning", Icon: Warning, tone: "text-warning", text: "text-warning-text" },
  { name: "Info", Icon: Info, tone: "text-info", text: "text-foreground" },
  { name: "Danger", Icon: XCircle, tone: "text-destructive", text: "text-destructive" },
]

const TYPE = [
  ["Display", "text-4xl font-semibold tracking-tight", "Ship the sprint"],
  ["Title", "text-xl font-semibold", "Project settings"],
  ["Heading", "text-base font-medium", "Recent activity"],
  ["Body", "text-sm", "Reading is open to every member; permissions only unlock writes."],
  ["Meta", "text-xs text-muted-foreground", "Updated 4 minutes ago by Maya Chen"],
  ["Mono", "font-mono text-xs", "PM-142  ·  8f3a-c21e"],
] as const

export function Foundations() {
  return (
    <Section id="foundations" title="Foundations" intro="Accent, neutrals, status, type and shape.">
      <Specimen title="Accent: Iris" note="Blue-violet, hue 295.">
        <div className="space-y-3 rounded-lg border p-4">
          <Scale />
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" icon={<Plus weight="bold" />}>New task</Button>
            <Badge variant="secondary">Label</Badge>
            <span className="text-sm font-medium text-primary underline-offset-4 hover:underline">Link text</span>
          </div>
        </div>
      </Specimen>

      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Neutrals" note="Tinted toward the accent hue">
          <div className="grid grid-cols-4 overflow-hidden rounded-md border sm:grid-cols-7">
            {NEUTRALS.map((n) => (
              <div key={n} className="flex h-20 flex-col justify-end p-1.5" style={{ background: `var(--${n})` }}>
                <span className={`text-caption leading-tight ${SWATCH_LABEL[n] ?? "text-foreground"}`}>{SWATCH_NAME[n] ?? n}</span>
              </div>
            ))}
          </div>
        </Specimen>
        <Specimen title="Status color" note="Icon plus text. Color alone never carries meaning.">
          <ul className="divide-y rounded-lg border">
            {STATUS_ROWS.map(({ name, Icon, tone, text }) => (
              <li key={name} className="flex h-10 items-center gap-2 px-3 text-sm">
                <Icon weight="fill" className={`size-4 ${tone}`} aria-hidden />
                <span className={text}>{name}</span>
              </li>
            ))}
          </ul>
        </Specimen>
      </div>

      <Specimen title="Type" note="Geist and Geist Mono. Tabular numerals in data.">
        <dl className="divide-y rounded-lg border">
          {TYPE.map(([name, cls, sample]) => (
            <div key={name} className="grid items-baseline gap-2 px-4 py-3 sm:grid-cols-[7rem_1fr]">
              <dt className="text-xs text-muted-foreground">{name}</dt>
              <dd className={cls}>{sample}</dd>
            </div>
          ))}
        </dl>
      </Specimen>

      <Specimen title="Radius and elevation" note="One radius family, shadows only on floating layers">
        <div className="flex flex-wrap items-end gap-4">
          {["rounded-sm", "rounded-md", "rounded-lg", "rounded-xl"].map((r) => (
            <div key={r} className={`flex h-14 w-24 items-center justify-center border bg-surface text-xs text-muted-foreground ${r}`}>
              {r.replace("rounded-", "")}
            </div>
          ))}
          <div className="flex h-14 w-32 items-center justify-center rounded-lg bg-popover text-xs text-muted-foreground shadow-pop">
            popover
          </div>
        </div>
      </Specimen>
    </Section>
  )
}
