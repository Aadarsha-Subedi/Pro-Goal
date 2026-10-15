import { useState } from "react"
import type { UseQueryResult } from "@tanstack/react-query"

/** A list of dropdown choices that is fetched when the dropdown is first opened, not when the page loads. */
export interface LazyOptions<T> {
  items: T[]
  loading: boolean
  error: boolean
  retry: () => void
  /** Call when the dropdown opens; starts the request once. */
  load: () => void
}

/**
 * `useList` is the query hook with `enabled` supplied by us. `force` loads without an open, for when the
 * page already holds a chosen value (a status in the URL) and needs its name to show.
 */
export function useLazyOptions<T>(useList: (enabled: boolean) => UseQueryResult<{ items: T[] }>, force = false): LazyOptions<T> {
  const [opened, setOpened] = useState(false)
  const q = useList(opened || force)
  return {
    items: q.data?.items ?? EMPTY,
    loading: q.isFetching && !q.data,
    error: q.isError && !q.data,
    retry: () => void q.refetch(),
    load: () => setOpened(true),
  }
}

const EMPTY: never[] = []

/** Options the page already has (the board needs them to build its lanes), in the same shape. */
export const readyOptions = <T,>(items: T[]): LazyOptions<T> => ({ items, loading: false, error: false, retry: () => {}, load: () => {} })
