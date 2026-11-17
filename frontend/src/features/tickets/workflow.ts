import type { User } from '../auth/hooks'
import type { Ticket, TicketStatus } from './hooks'

export type TransitionTarget = TicketStatus

export function isOwner(user: User | null, ticket: Ticket) {
  return !!user && user.id === ticket.requester.id
}

export function isStaff(user: User | null) {
  return user?.role === 'agent' || user?.role === 'admin'
}

export function allowedTransitions(
  status: TicketStatus,
  user: User | null,
  ticket: Ticket,
): TransitionTarget[] {
  const owner = isOwner(user, ticket)
  const staff = isStaff(user)
  const admin = user?.role === 'admin'

  switch (status) {
    case 'OPEN':
      return staff ? ['IN_PROGRESS', 'CLOSED'] : []
    case 'IN_PROGRESS':
      if (!staff) return []
      return admin ? ['WAITING_ON_USER', 'RESOLVED', 'OPEN'] : ['WAITING_ON_USER', 'RESOLVED']
    case 'WAITING_ON_USER':
      if (!staff) return []
      return admin
        ? ['IN_PROGRESS', 'RESOLVED', 'CLOSED']
        : ['IN_PROGRESS', 'RESOLVED']
    case 'RESOLVED':
      if (admin || staff) {
        return owner ? ['CLOSED', 'OPEN'] : ['CLOSED', 'OPEN']
      }
      return owner ? ['CLOSED', 'OPEN'] : []
    case 'CLOSED':
      return admin ? ['OPEN'] : []
    default:
      return []
  }
}

export function transitionRequirements(target: TransitionTarget) {
  switch (target) {
    case 'CLOSED':
      // Only required when coming from OPEN; caller can still provide it.
      return { resolutionNote: false, reason: false, comment: false }
    case 'RESOLVED':
      return { resolutionNote: true, reason: false, comment: false }
    case 'WAITING_ON_USER':
      return { resolutionNote: false, reason: false, comment: true }
    case 'OPEN':
      return { resolutionNote: false, reason: true, comment: false }
    case 'IN_PROGRESS':
      return { resolutionNote: false, reason: false, comment: false }
    default:
      return { resolutionNote: false, reason: false, comment: false }
  }
}
