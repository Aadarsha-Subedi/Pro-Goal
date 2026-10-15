import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Kbd } from "@/components/ui/kbd"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { ArrowRight, Check, DownloadSimple, Funnel, GearSix, Kanban, ListBullets, Plus, SquaresFour, Trash, DotsThree, Share } from "@/icons"
import { Section, Specimen } from "../section"

const VARIANTS = ["default", "secondary", "outline", "ghost", "destructive", "link"] as const

export function Actions() {
  return (
    <Section id="actions" title="Buttons" intro="Every action is a button with an icon. This page shows every state side by side; in a real view there is one primary button. Icon-only buttons need a label, which becomes the tooltip and the accessible name.">
      <Specimen title="Variants" note="default · hover · focus · disabled · loading">
        <div className="divide-y rounded-lg border">
          {VARIANTS.map((v) => (
            <div key={v} className="grid items-center gap-3 px-4 py-3 sm:grid-cols-[6rem_1fr]">
              <span className="text-xs text-muted-foreground">{v}</span>
              <div className="flex flex-wrap items-center gap-2">
                <Button variant={v} icon={v === "destructive" ? <Trash /> : <Check weight="bold" />}>{v === "destructive" ? "Delete task" : "Approve"}</Button>
                <Button variant={v} iconEnd={<ArrowRight weight="bold" />}>{v === "destructive" ? "Review impact" : "Open project"}</Button>
                <Button variant={v} disabled icon={v === "destructive" ? <Trash /> : <Check weight="bold" />}>{v === "destructive" ? "Delete task" : "Approve"}</Button>
                <Button variant={v} loading>{v === "destructive" ? "Deleting" : "Approving"}</Button>
                <Button variant={v} size="icon" label="More options"><DotsThree weight="bold" /></Button>
              </div>
            </div>
          ))}
        </div>
      </Specimen>

      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Sizes">
          <div className="flex flex-wrap items-center gap-2">
            <Button size="xs" icon={<Plus weight="bold" />}>xs</Button>
            <Button size="sm" icon={<Plus weight="bold" />}>sm</Button>
            <Button icon={<Plus weight="bold" />}>default</Button>
            <Button size="lg" icon={<Plus weight="bold" />}>lg</Button>
          </div>
        </Specimen>
        <Specimen title="With shortcut hint">
          <div className="flex flex-wrap items-center gap-2">
            <Button icon={<Plus weight="bold" />}>New task <Kbd className="ml-1 bg-black/20 text-primary-foreground">C</Kbd></Button>
            <Button variant="outline" icon={<Funnel />}>Filter <Kbd className="ml-1">F</Kbd></Button>
          </div>
        </Specimen>
      </div>

      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Button group">
          <div className="flex flex-wrap items-center gap-3">
            <ButtonGroup>
              <Button variant="outline" icon={<Share />}>Share</Button>
              <Button variant="outline" icon={<DownloadSimple />}>Export</Button>
              <Button variant="outline" size="icon" label="Settings"><GearSix /></Button>
            </ButtonGroup>
            <Button variant="destructive" icon={<Trash />}>Delete</Button>
          </div>
        </Specimen>
        <Specimen title="Segmented toggle" note="View switcher">
          <ToggleGroup variant="outline" defaultValue={["list"]}>
            <ToggleGroupItem value="list" aria-label="List"><ListBullets /> List</ToggleGroupItem>
            <ToggleGroupItem value="board" aria-label="Board"><Kanban /> Board</ToggleGroupItem>
            <ToggleGroupItem value="grid" aria-label="Grid"><SquaresFour /> Grid</ToggleGroupItem>
          </ToggleGroup>
        </Specimen>
      </div>
    </Section>
  )
}
