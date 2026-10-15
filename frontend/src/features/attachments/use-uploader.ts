import { useCallback, useEffect, useRef, useState } from "react"
import type { Target } from "./api"
import { runUpload, type UploadState } from "./pipeline"
import { useAttachmentMutations } from "./queries"

const CONCURRENCY = 2

/** A queue of uploads for one target: two at a time, each cancellable and retryable. */
export function useUploader(projectId: string, target: Target) {
  const [items, setItems] = useState<UploadState[]>([])
  const files = useRef(new Map<string, File>())
  const controllers = useRef(new Map<string, AbortController>())
  const queue = useRef<string[]>([])
  const running = useRef(0)
  const { refresh } = useAttachmentMutations(projectId)
  const targetRef = useRef(target)
  useEffect(() => { targetRef.current = target })
  const alive = useRef(true)
  // StrictMode mounts, unmounts and remounts once in development: the flag must come back on remount or progress is dropped.
  useEffect(() => {
    alive.current = true
    const live = controllers.current
    return () => { alive.current = false; live.forEach((c) => c.abort()) }
  }, [])

  const patch = useCallback((s: UploadState) => alive.current && setItems((all) => all.map((x) => (x.id === s.id ? s : x))), [])

  const pumpRef = useRef<() => void>(() => {})
  const pump = useCallback(() => {
    while (running.current < CONCURRENCY && queue.current.length > 0) {
      const id = queue.current.shift()!
      const file = files.current.get(id)
      if (!file) continue
      const ac = new AbortController()
      controllers.current.set(id, ac)
      running.current++
      void runUpload(projectId, targetRef.current, file, id, patch, ac.signal).finally(() => {
        running.current--
        controllers.current.delete(id)
        void refresh()
        pumpRef.current()
      })
    }
  }, [projectId, patch, refresh])
  useEffect(() => { pumpRef.current = pump })

  const add = useCallback((list: File[]) => {
    const fresh = list.map((f) => ({ id: crypto.randomUUID(), file: f }))
    for (const { id, file } of fresh) files.current.set(id, file)
    setItems((all) => [...all, ...fresh.map(({ id, file }): UploadState => ({ id, name: file.name, size: file.size, phase: "uploading", progress: 0 }))])
    queue.current.push(...fresh.map((f) => f.id))
    pump()
  }, [pump])

  const cancel = useCallback((id: string) => {
    queue.current = queue.current.filter((q) => q !== id)
    const ac = controllers.current.get(id)
    if (ac) ac.abort()
    else setItems((all) => all.map((x) => (x.id === id ? { ...x, phase: "cancelled" } : x)))
  }, [])
  const retry = useCallback((id: string) => {
    setItems((all) => all.map((x) => (x.id === id ? { ...x, phase: "uploading", progress: 0, error: undefined } : x)))
    queue.current.push(id)
    pump()
  }, [pump])
  const dismiss = useCallback((id: string) => {
    files.current.delete(id)
    setItems((all) => all.filter((x) => x.id !== id))
  }, [])
  const busy = items.some((i) => i.phase === "uploading" || i.phase === "confirming" || i.phase === "processing")
  return { items, add, cancel, retry, dismiss, busy }
}
