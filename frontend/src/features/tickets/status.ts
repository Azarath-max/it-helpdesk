import type { TicketPriority, TicketStatus } from './hooks'

export const statusLabels: Record<TicketStatus, string> = {
  OPEN: 'Open',
  IN_PROGRESS: 'In progress',
  WAITING_ON_USER: 'Waiting on user',
  RESOLVED: 'Resolved',
  CLOSED: 'Closed',
}

export const priorityLabels: Record<TicketPriority, string> = {
  LOW: 'Low',
  MEDIUM: 'Medium',
  HIGH: 'High',
  URGENT: 'Urgent',
}

export const statusClasses: Record<TicketStatus, string> = {
  OPEN: 'bg-slate-100 text-slate-700 ring-slate-500/20',
  IN_PROGRESS: 'bg-sky-100 text-sky-800 ring-sky-600/20',
  WAITING_ON_USER: 'bg-amber-100 text-amber-900 ring-amber-600/20',
  RESOLVED: 'bg-emerald-100 text-emerald-800 ring-emerald-600/20',
  CLOSED: 'bg-slate-200 text-slate-600 ring-slate-500/20',
}

export const priorityClasses: Record<TicketPriority, string> = {
  LOW: 'text-slate-500',
  MEDIUM: 'text-slate-700',
  HIGH: 'text-amber-700',
  URGENT: 'text-rose-700',
}
