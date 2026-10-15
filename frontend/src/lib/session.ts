import { redirect } from '@tanstack/react-router'
import { authApi, type Me } from '@/features/auth/api'
import { ApiError } from '@/lib/api'
import { saveInviteCode, takeInviteCode } from '@/lib/invite'
import { cachedSession } from '@/lib/session-cache'

export type Session = { status: 'signed-in'; me: Me } | { status: 'incomplete' } | { status: 'anonymous' }

/** Asks the backend who the cookie belongs to. Network failures throw so guards never guess. */
export function getSession(): Promise<Session> {
  return cachedSession(fetchSession, (s) => s.status === 'signed-in')
}

async function fetchSession(): Promise<Session> {
  try {
    return { status: 'signed-in', me: await authApi.me() }
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.code === 'profile_incomplete') return { status: 'incomplete' }
      if (e.status === 401 || e.status === 403) return { status: 'anonymous' }
    }
    throw e
  }
}

/** Public-only routes (landing, login, signup): a signed-in user goes to the app. */
export async function guestOnly({ search }: { search?: { code?: string } } = {}) {
  if (search?.code) saveInviteCode(search.code)
  let session: Session
  try {
    session = await getSession()
  } catch {
    return // backend unreachable: show the public page rather than a dead screen
  }
  if (session.status === 'signed-in') {
    const code = takeInviteCode()
    if (code) throw redirect({ to: '/join', search: { code }, replace: true })
    throw redirect({ to: '/app', replace: true })
  }
  if (session.status === 'incomplete') throw redirect({ to: '/complete-profile', replace: true })
}

/** Private routes: anonymous goes to login, an unfinished profile goes to complete-profile. */
export async function requireSession(): Promise<{ me: Me }> {
  const session = await getSession()
  if (session.status === 'anonymous') throw redirect({ to: '/login', replace: true })
  if (session.status === 'incomplete') throw redirect({ to: '/complete-profile', replace: true })
  return { me: session.me }
}

/** Complete-profile: needs a session, but only while the profile is unfinished. */
export async function requireIncompleteProfile() {
  const session = await getSession()
  if (session.status === 'anonymous') throw redirect({ to: '/login', replace: true })
  if (session.status === 'signed-in') throw redirect({ to: '/app', replace: true })
}

/** Invite links: anonymous visitors go to signup with the code kept, everyone else to the join step. */
export async function requireSessionForJoin({ search }: { search: { code?: string } }): Promise<{ me: Me }> {
  const session = await getSession()
  // Only a visitor without an account needs the code kept; a signed-in user uses it right here.
  if (session.status === 'anonymous') {
    if (search.code) saveInviteCode(search.code)
    throw redirect({ to: '/signup', search: { join: true }, replace: true })
  }
  if (session.status === 'incomplete') {
    if (search.code) saveInviteCode(search.code)
    throw redirect({ to: '/complete-profile', replace: true })
  }
  return { me: session.me }
}
