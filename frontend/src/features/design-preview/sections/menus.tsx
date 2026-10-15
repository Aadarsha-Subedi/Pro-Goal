import { useEffect, useState } from "react"
import { toast } from "sonner"
import { DeleteProjectDialog } from "@/components/patterns/delete-project-dialog"
import { JoinProjectDialog } from "@/components/patterns/join-dialog"
import { STATUSES, StatusLabel } from "@/components/patterns/status"
import { Button } from "@/components/ui/button"
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandShortcut } from "@/components/ui/command"
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger } from "@/components/ui/context-menu"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuShortcut, DropdownMenuSub, DropdownMenuSubContent, DropdownMenuSubTrigger, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { ArrowsLeftRight, Check, CaretDown, CheckSquare, Copy, DotsThree, Funnel, MagnifyingGlass, PencilSimple, Plus, Trash, UserPlus } from "@/icons"
import { Section, Specimen } from "../section"


export function Menus() {
  const [cmd, setCmd] = useState(false)
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setCmd((v) => !v)
      }
    }
    window.addEventListener("keydown", on)
    return () => window.removeEventListener("keydown", on)
  }, [])

  return (
    <Section id="menus" title="Menus and overlays" intro="Action menus, context menus, command palette, dialogs. Modals only where focus must be protected; everything else is a popover or sheet.">
      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Action menu" note="Row actions, with submenu, shortcuts, destructive item">
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="outline" iconEnd={<CaretDown />} icon={<DotsThree weight="bold" />}>Actions</Button>} />
            <DropdownMenuContent className="w-56">
              <DropdownMenuGroup>
                <DropdownMenuLabel>Task PM-142</DropdownMenuLabel>
                <DropdownMenuItem><PencilSimple /> Edit <DropdownMenuShortcut>E</DropdownMenuShortcut></DropdownMenuItem>
                <DropdownMenuItem><Copy /> Duplicate <DropdownMenuShortcut>⌘D</DropdownMenuShortcut></DropdownMenuItem>
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger><ArrowsLeftRight /> Move to</DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    {STATUSES.map((st) => (
                      <DropdownMenuItem key={st} className="justify-between">
                        <StatusLabel status={st} />
                        {st === "progress" && <Check weight="bold" aria-label="Current status" className="size-3.5" />}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuItem><UserPlus /> Assign…</DropdownMenuItem>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive"><Trash /> Delete <DropdownMenuShortcut>⌫</DropdownMenuShortcut></DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </Specimen>

        <Specimen title="Context menu" note="Right-click the area">
          <ContextMenu>
            <ContextMenuTrigger className="flex h-24 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
              Right-click a task row
            </ContextMenuTrigger>
            <ContextMenuContent className="w-48">
              <ContextMenuItem><PencilSimple /> Edit</ContextMenuItem>
              <ContextMenuItem><Copy /> Duplicate</ContextMenuItem>
              <ContextMenuItem variant="destructive"><Trash /> Delete</ContextMenuItem>
            </ContextMenuContent>
          </ContextMenu>
        </Specimen>
      </div>

      <div className="grid gap-10 lg:grid-cols-2">
        <Specimen title="Command palette" note="Cmd/Ctrl + K">
          <Button variant="outline" icon={<MagnifyingGlass />} onClick={() => setCmd(true)} className="text-muted-foreground">
            Search or jump to… <span className="ml-6 text-xs">⌘K</span>
          </Button>
          <CommandDialog open={cmd} onOpenChange={setCmd}>
            <CommandInput placeholder="Type a command or search…" />
            <CommandList>
              <CommandEmpty>No results.</CommandEmpty>
              <CommandGroup heading="Actions">
                <CommandItem><Plus /> Create task <CommandShortcut>C</CommandShortcut></CommandItem>
                <CommandItem><CheckSquare /> Go to my tasks <CommandShortcut>G T</CommandShortcut></CommandItem>
                <CommandItem><Funnel /> Filter by status <CommandShortcut>F</CommandShortcut></CommandItem>
              </CommandGroup>
            </CommandList>
          </CommandDialog>
        </Specimen>

        <Specimen title="Popover and quick create">
          <div className="flex flex-wrap gap-2">
            <Popover>
              <PopoverTrigger render={<Button variant="outline" icon={<Funnel />}>Filters</Button>} />
              <PopoverContent className="w-64">
                <p className="text-sm font-medium">Quick filters</p>
                <p className="mt-1 text-xs text-muted-foreground">Small, non-blocking surface anchored to its button.</p>
              </PopoverContent>
            </Popover>
            <Dialog>
              <DialogTrigger render={<Button icon={<Plus weight="bold" />}>New task</Button>} />
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>New task</DialogTitle>
                  <DialogDescription>Centered, focused, dismissed with Esc. Detail editing opens as a full page, not a side panel.</DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                  <Input placeholder="Task title" autoFocus />
                  <Textarea placeholder="Add a description…" />
                </div>
                <DialogFooter>
                  <Button icon={<Plus weight="bold" />} onClick={() => toast.success("Task created")}>Create task</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </Specimen>
      </div>

      <Specimen title="Dialogs" note="Dialog for forms that need focus, alert dialog for destructive confirms. Join codes to try: AAAAAA (not found), EXPIRE (expired), MEMBER (already a member).">
        <div className="flex flex-wrap gap-2">
          <JoinProjectDialog />
          <DeleteProjectDialog />
        </div>
      </Specimen>
    </Section>
  )
}
