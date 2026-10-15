import { useRef, useState } from "react"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Avatar, AvatarFallback, AvatarGroup, AvatarGroupCount } from "@/components/ui/avatar"
import { Combobox, ComboboxChip, ComboboxChips, ComboboxChipsInput, ComboboxContent, ComboboxEmpty, ComboboxInput, ComboboxItem, ComboboxList, ComboboxValue, useComboboxAnchor } from "@/components/ui/combobox"
import { ActivityFeed } from "@/components/patterns/activity-feed"
import { CommentThread } from "@/components/patterns/comment-thread"
import { DatePicker } from "@/components/patterns/date-picker"
import { FileDropzone } from "@/components/patterns/file-dropzone"
import { MarkdownEditor } from "@/components/patterns/markdown-editor"
import { Section, Specimen } from "../section"

const PEOPLE = ["Maya Chen", "Dev Patel", "Sam Rivera", "Ana Souza", "Liam Novak"]
const TAGS = ["auth", "api", "tracker", "slack", "files", "projects", "explore"]
const ini = (n: string) => n.split(" ").map((p) => p[0]).join("")

function TagCombobox() {
  const anchor = useComboboxAnchor()
  const [value, setValue] = useState<string[]>(["auth", "api"])
  return (
    <Combobox multiple items={TAGS} value={value} onValueChange={setValue}>
      <ComboboxChips ref={anchor}>
        <ComboboxValue>
          {(vals: string[]) => (
            <>
              {vals.map((v) => <ComboboxChip key={v}>{v}</ComboboxChip>)}
              <ComboboxChipsInput aria-label="Add tag" placeholder={vals.length ? "" : "Add tags"} />
            </>
          )}
        </ComboboxValue>
      </ComboboxChips>
      <ComboboxContent anchor={anchor}>
        <ComboboxEmpty>No tags found.</ComboboxEmpty>
        <ComboboxList>{(item: string) => <ComboboxItem key={item} value={item}>{item}</ComboboxItem>}</ComboboxList>
      </ComboboxContent>
    </Combobox>
  )
}

export function Content() {
  const ref = useRef(null)
  return (
    <Section id="content" title="Content and collaboration" intro="Pickers, uploads, notes, comments and activity. All flat: rails, dividers and rows instead of boxed cards.">
      <div className="grid gap-12 lg:grid-cols-2">
        <Specimen title="Combobox" note="Single select with search, and multi-select tags">
          <div className="space-y-3" ref={ref}>
            <Combobox items={PEOPLE}>
              <ComboboxInput placeholder="Assign to…" />
              <ComboboxContent>
                <ComboboxEmpty>No members found.</ComboboxEmpty>
                <ComboboxList>{(item: string) => <ComboboxItem key={item} value={item}>{item}</ComboboxItem>}</ComboboxList>
              </ComboboxContent>
            </Combobox>
            <TagCombobox />
          </div>
        </Specimen>
        <Specimen title="Date picker" note="Plain dates, no time zones">
          <DatePicker placeholder="Due date" />
        </Specimen>
      </div>

      <div className="grid gap-12 lg:grid-cols-2">
        <Specimen title="Avatar group">
          <AvatarGroup className="-space-x-1">
            {PEOPLE.slice(0, 4).map((p) => <Avatar key={p}><AvatarFallback>{ini(p)}</AvatarFallback></Avatar>)}
            <AvatarGroupCount>+3</AvatarGroupCount>
          </AvatarGroup>
        </Specimen>
        <Specimen title="Accordion" note="Collapsible settings and FAQs">
          <Accordion className="rounded-lg border px-4">
            <AccordionItem value="a"><AccordionTrigger>Who can edit due dates?</AccordionTrigger><AccordionContent>Members with the due date permission, and the owner.</AccordionContent></AccordionItem>
            <AccordionItem value="b"><AccordionTrigger>What happens when I leave?</AccordionTrigger><AccordionContent>Your tasks are reassigned to the owner.</AccordionContent></AccordionItem>
          </Accordion>
        </Specimen>
      </div>

      <Specimen title="File upload" note="Drop or browse; direct-to-storage upload comes later">
        <FileDropzone onFiles={() => {}} />
      </Specimen>

      <Specimen title="Note editor" note="Markdown with Write and Preview. Raw HTML is never rendered.">
        <MarkdownEditor defaultValue={"## Sprint notes\n\n- Ship **auth** fixes\n- Review `join` flow\n\nSee [the plan](https://example.com)."} />
      </Specimen>

      <div className="grid gap-12 lg:grid-cols-2">
        <Specimen title="Comments">
          <CommentThread comments={[
            { id: "1", author: "Dev Patel", time: "2 hours ago", body: "Repro'd on Safari only. Looking at the redirect." },
            { id: "2", author: "Maya Chen", time: "40 minutes ago", body: "Fixed in the verification handler, PR is up." },
          ]} />
        </Specimen>
        <Specimen title="Activity feed">
          <ActivityFeed items={[
            { id: "1", actor: "Maya Chen", action: "moved PM-142 to In progress", time: "4 minutes ago" },
            { id: "2", actor: "Dev Patel", action: "commented on PM-142", time: "1 hour ago" },
            { id: "3", actor: "Sam Rivera", action: "changed priority of PM-137 to Low", time: "Yesterday" },
          ]} />
        </Specimen>
      </div>
    </Section>
  )
}
