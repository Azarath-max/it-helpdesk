import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Card,
  FormAlert,
  SubmitButton,
  TextAreaField,
  TextField,
} from '../components/ui'
import { useSession } from '../features/auth/hooks'
import { useTicket, useUpdateTicket } from '../features/tickets/hooks'
import type { Ticket, TicketUpdateInput } from '../features/tickets/hooks'
import { priorityClasses, priorityLabels, statusClasses, statusLabels } from '../features/tickets/status'

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function Badge({ className, children }: { className: string; children: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${className}`}
    >
      {children}
    </span>
  )
}

function canEdit(user: { id: string; role: string }, ticket: Ticket) {
  if (user.role === 'agent' || user.role === 'admin') {
    return true
  }
  return user.id === ticket.requester.id && ticket.status === 'OPEN'
}

export function TicketDetailPage() {
  const { id = '' } = useParams()
  const session = useSession()
  const ticket = useTicket(id)
  const updateTicket = useUpdateTicket(id)
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const user = session.data

  function startEditing(current: Ticket) {
    setTitle(current.title)
    setDescription(current.description)
    setCategory(current.category ?? '')
    setEditing(true)
  }

  function cancelEditing() {
    setEditing(false)
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!ticket.data) {
      return
    }
    const payload: TicketUpdateInput = {
      title,
      description,
      category: category.trim() || null,
      version: ticket.data.version,
    }
    updateTicket.mutate(payload, {
      onSuccess: () => setEditing(false),
    })
  }

  if (ticket.isPending) {
    return <p className="py-10 text-center text-sm text-slate-500">Loading ticket…</p>
  }
  if (ticket.isError || !ticket.data) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <FormAlert>{ticket.error?.message ?? 'Ticket not found.'}</FormAlert>
        <Link to="/tickets" className="text-sm font-medium text-slate-900 hover:underline">
          Back to tickets
        </Link>
      </div>
    )
  }

  const current = ticket.data
  const editable = user ? canEdit(user, current) : false

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/tickets" className="text-xs font-medium text-slate-500 hover:text-slate-900">
            ← Back to tickets
          </Link>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
            {current.title}
          </h1>
          <p className="font-mono text-xs text-slate-500">{current.publicRef}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={statusClasses[current.status]}>
            {statusLabels[current.status]}
          </Badge>
          <Badge className={priorityClasses[current.priority]}>
            {`${priorityLabels[current.priority]} priority`}
          </Badge>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Details</h2>
          <dl className="mt-3 space-y-3 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Requester</dt>
              <dd className="text-slate-700">{current.requester.name}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Assignee</dt>
              <dd className="text-slate-700">
                {current.assignee ? current.assignee.name : 'Unassigned'}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Category</dt>
              <dd className="text-slate-700">{current.category ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Created</dt>
              <dd className="text-slate-700">{formatDate(current.createdAt)}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Updated</dt>
              <dd className="text-slate-700">{formatDate(current.updatedAt)}</dd>
            </div>
            {current.resolvedAt ? (
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-400">Resolved</dt>
                <dd className="text-slate-700">{formatDate(current.resolvedAt)}</dd>
              </div>
            ) : null}
            {current.closedAt ? (
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-400">Closed</dt>
                <dd className="text-slate-700">{formatDate(current.closedAt)}</dd>
              </div>
            ) : null}
          </dl>
        </Card>

        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Description</h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
            {current.description}
          </p>
          <p className="mt-4 text-xs text-slate-400">
            Version {current.version} · {current.source}
          </p>
        </Card>
      </div>

      {editable ? (
        <Card>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-slate-900">Edit</h2>
            {!editing ? (
              <button
                type="button"
                onClick={() => startEditing(current)}
                className="text-xs font-semibold text-slate-700 hover:underline"
              >
                Edit details
              </button>
            ) : null}
          </div>

          {editing ? (
            <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
              <TextField
                label="Title"
                type="text"
                required
                minLength={3}
                maxLength={160}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
              <TextAreaField
                label="Description"
                required
                minLength={1}
                maxLength={5000}
                rows={6}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
              <TextField
                label="Category"
                type="text"
                maxLength={60}
                value={category}
                onChange={(event) => setCategory(event.target.value)}
              />
              {updateTicket.isError ? (
                <FormAlert>{updateTicket.error.message}</FormAlert>
              ) : null}
              <div className="flex gap-3">
                <SubmitButton pending={updateTicket.isPending}>Save changes</SubmitButton>
                <button
                  type="button"
                  onClick={cancelEditing}
                  className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <p className="mt-2 text-xs text-slate-500">
              Title, description, and category can be changed. Priority and status are managed
              separately.
            </p>
          )}
        </Card>
      ) : null}
    </div>
  )
}
