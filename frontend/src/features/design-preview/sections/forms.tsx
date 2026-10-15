import { useState } from "react"
import { Checkbox } from "@/components/ui/checkbox"
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Eye, EyeSlash, EnvelopeSimple, FloppyDisk, X } from "@/icons"
import { Section, Specimen } from "../section"

export function Forms() {
  const [show, setShow] = useState(false)
  const [tags, setTags] = useState(["backend", "auth"])
  return (
    <Section id="forms" title="Forms" intro="Label above, hint below, error replaces the hint. Controls share one height so rows align.">
      <div className="grid gap-12 lg:grid-cols-2">
        <Specimen title="Text inputs">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="email">Email</FieldLabel>
              <div className="relative">
                <EnvelopeSimple className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="email" placeholder="you@team.com" className="pl-8" />
              </div>
              <FieldDescription>We send a verification link, valid 24 hours.</FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="pw">Password</FieldLabel>
              <div className="relative">
                <Input id="pw" type={show ? "text" : "password"} defaultValue="correct horse" className="pr-9" />
                <Button type="button" variant="ghost" size="icon-xs" label={show ? "Hide password" : "Show password"} className="absolute inset-y-0 right-1.5 my-auto" onClick={() => setShow(!show)}>
                  {show ? <EyeSlash /> : <Eye />}
                </Button>
              </div>
            </Field>
            <Field data-invalid>
              <FieldLabel htmlFor="code">Join code</FieldLabel>
              <Input id="code" defaultValue="AB12" aria-invalid />
              <FieldError>Codes are 6 characters.</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="desc">Description</FieldLabel>
              <Textarea id="desc" placeholder="What is this project about?" />
            </Field>
            <Field>
              <FieldLabel>Verification code</FieldLabel>
              <InputOTP maxLength={6} aria-label="Verification code">
                <InputOTPGroup>
                  {[0, 1, 2, 3, 4, 5].map((i) => <InputOTPSlot key={i} index={i} />)}
                </InputOTPGroup>
              </InputOTP>
            </Field>
          </FieldGroup>
        </Specimen>

        <Specimen title="Choices">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="status">Status</FieldLabel>
              <Select defaultValue="progress" items={[{ value: "todo", label: "Todo" }, { value: "progress", label: "In progress" }, { value: "done", label: "Done" }]}>
                <SelectTrigger id="status" className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="todo">Todo</SelectItem>
                  <SelectItem value="progress">In progress</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel htmlFor="tags">Tags</FieldLabel>
              <div className="flex flex-wrap items-center gap-1.5 rounded-md border px-2 py-1.5">
                {tags.map((t) => (
                  <span key={t} className="inline-flex h-6 items-center gap-1 rounded bg-secondary pr-1 pl-2 text-xs">
                    {t}
                    <Button type="button" variant="ghost" size="icon-xs" label={`Remove ${t}`} onClick={() => setTags(tags.filter((x) => x !== t))}><X weight="bold" /></Button>
                  </span>
                ))}
                <input id="tags" className="min-w-20 flex-1 bg-transparent text-sm outline-none" placeholder="Add tag" onKeyDown={(e) => {
                  if (e.key === "Enter" && e.currentTarget.value.trim()) { setTags([...tags, e.currentTarget.value.trim()]); e.currentTarget.value = "" }
                }} />
              </div>
            </Field>
            <Field orientation="horizontal">
              <Checkbox id="c1" defaultChecked />
              <FieldLabel htmlFor="c1">Email me when a task is assigned to me</FieldLabel>
            </Field>
            <Field orientation="horizontal">
              <Switch id="s1" defaultChecked />
              <FieldLabel htmlFor="s1">Send updates to Slack</FieldLabel>
            </Field>
            <Field>
              <FieldLabel>Storage quota</FieldLabel>
              <Slider defaultValue={[40]} aria-label="Storage quota" />
            </Field>
            <div><Button icon={<FloppyDisk />}>Save changes</Button></div>
          </FieldGroup>
        </Specimen>
      </div>
    </Section>
  )
}
