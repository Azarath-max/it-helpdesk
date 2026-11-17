import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Card,
  FormAlert,
  SelectField,
  SubmitButton,
  TextAreaField,
  TextField,
} from '../components/ui'
import { useSession } from '../features/auth/hooks'
import { useUsers } from '../features/users/hooks'
import {
  useAssignTicket,
  useComments,
  useCreateComment,
  useDeleteComment,
  useTicket,
  useTransitionTicket,
  useUpdateTicket,
} from '../features/tickets/hooks'
import type { Comment, Ticket, TransitionTicketInput } from '../features/tickets/hooks'
import { allowedTransitions, transitionRequirements } from '../features/tickets/workflow'
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

function TransitionPanel({ ticket }: { ticket: Ticket }) {
  const session = useSession()
  const user = session.data
  const transition = useTransitionTicket(ticket.id)
  const [target, setTarget] = useState('')
  const [resolutionNote, setResolutionNote] = useState('')
  const [reason, setReason] = useState('')
  const [comment, setComment] = useState('')

  if (!user) return null

  const options = allowedTransitions(ticket.status, user, ticket)
  if (options.length === 0) return null

  const req = target ? transitionRequirements(target as never) : null

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!target) return
    const payload: TransitionTicketInput = {
      status: target as TransitionTicketInput['status'],
      version: ticket.version,
      resolutionNote: req?.resolutionNote ? resolutionNote : null,
      reason: req?.reason ? reason : null,
      comment: req?.comment ? comment : null,
    }
    transition.mutate(payload, {
      onSuccess: () => {
        setTarget('')
        setResolutionNote('')
        setReason('')
        setComment('')
      },
    })
  }

  return (
    <Card>
      <h2 className="text-sm font-semibold text-slate-900">Change status</h2>
      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <SelectField
          label="New status"
          value={target}
          onChange={(event) => setTarget(event.target.value)}
        >
          <option value="">Select a transition</option>
          {options.map((option) => (
            <option key={option} value={option}>
              {option.replace(/_/g, ' ')}
            </option>
          ))}
        </SelectField>
        {req?.resolutionNote ? (
          <TextAreaField
            label="Resolution note"
            required
            rows={4}
            value={resolutionNote}
            onChange={(event) => setResolutionNote(event.target.value)}
          />
        ) : null}
        {req?.reason ? (
          <TextAreaField
            label="Reason"
            required
            rows={3}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        ) : null}
        {req?.comment ? (
          <TextAreaField
            label="Comment to requester"
            required
            rows={3}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
        ) : null}
        {transition.isError ? <FormAlert>{transition.error.message}</FormAlert> : null}
        <SubmitButton pending={transition.isPending} disabled={!target}>
          Apply transition
        </SubmitButton>
      </form>
    </Card>
  )
}

function AssignmentPanel({ ticket }: { ticket: Ticket }) {
  const session = useSession()
  const user = session.data
  const assign = useAssignTicket(ticket.id)
  const users = useUsers(user?.role === 'admin')
  const [assigneeId, setAssigneeId] = useState(ticket.assignee?.id ?? '')

  if (!user || (user.role !== 'agent' && user.role !== 'admin')) return null

  const isAdmin = user.role === 'admin'
  const staff = users.data?.items.filter((item) => item.role === 'agent' || item.role === 'admin') ?? []

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    assign.mutate(
      {
        assigneeId: assigneeId || null,
        version: ticket.version,
      },
      {
        onSuccess: () => undefined,
      },
    )
  }

  return (
    <Card>
      <h2 className="text-sm font-semibold text-slate-900">Assignment</h2>
      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        {isAdmin ? (
          <SelectField
            label="Assignee"
            value={assigneeId}
            onChange={(event) => setAssigneeId(event.target.value)}
          >
            <option value="">Unassigned</option>
            {staff.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.name} ({candidate.role})
              </option>
            ))}
          </SelectField>
        ) : (
          <p className="text-sm text-slate-600">
            {ticket.assignee ? `Assigned to ${ticket.assignee.name}.` : 'Unassigned.'}
          </p>
        )}
        {assign.isError ? <FormAlert>{assign.error.message}</FormAlert> : null}
        <div className="flex flex-wrap gap-2">
          {isAdmin ? (
            <SubmitButton pending={assign.isPending}>Save assignment</SubmitButton>
          ) : null}
          {!ticket.assignee || ticket.assignee.id !== user.id ? (
            <button
              type="button"
              onClick={() =>
                assign.mutate({ assigneeId: user.id, version: ticket.version })
              }
              disabled={assign.isPending}
              className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
            >
              Claim ticket
            </button>
          ) : null}
        </div>
      </form>
    </Card>
  )
}

function CommentList({ ticket }: { ticket: Ticket }) {
  const session = useSession()
  const user = session.data
  const comments = useComments(ticket.id)
  const createComment = useCreateComment(ticket.id)
  const deleteComment = useDeleteComment()
  const [body, setBody] = useState('')
  const [visibility, setVisibility] = useState<'PUBLIC' | 'INTERNAL'>('PUBLIC')

  const staff = user?.role === 'agent' || user?.role === 'admin'

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    createComment.mutate(
      { body, visibility },
      {
        onSuccess: () => setBody(''),
      },
    )
  }

  function canDelete(comment: Comment) {
    if (!user) return false
    if (user.role === 'admin') return true
    if (comment.author?.id !== user.id) return false
    // eslint-disable-next-line react/purity
    const age = Date.now() - new Date(comment.createdAt).getTime()
    return age <= 5 * 60 * 1000
  }

  return (
    <Card>
      <h2 className="text-sm font-semibold text-slate-900">Comments</h2>
      {comments.isPending ? (
        <p className="mt-3 text-sm text-slate-500">Loading comments…</p>
      ) : comments.isError ? (
        <FormAlert>{comments.error.message}</FormAlert>
      ) : comments.data.items.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">No comments yet.</p>
      ) : (
        <ul className="mt-4 space-y-4">
          {comments.data.items.map((comment) => (
            <li key={comment.id} className="rounded-lg border border-slate-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs text-slate-500">
                  <span className="font-medium text-slate-700">
                    {comment.author?.name ?? 'Unknown'}
                  </span>{' '}
                  · {formatDate(comment.createdAt)}
                </div>
                <div className="flex items-center gap-2">
                  {comment.visibility === 'INTERNAL' ? (
                    <Badge className="bg-amber-100 text-amber-900 ring-amber-600/20">
                      Internal note
                    </Badge>
                  ) : null}
                  {comment.deletedAt ? (
                    <Badge className="bg-slate-200 text-slate-500 ring-slate-500/20">
                      Deleted
                    </Badge>
                  ) : null}
                  {canDelete(comment) && !comment.deletedAt ? (
                    <button
                      type="button"
                      onClick={() => deleteComment.mutate(comment.id)}
                      disabled={deleteComment.isPending}
                      className="text-xs font-medium text-rose-700 hover:underline disabled:opacity-60"
                    >
                      Delete
                    </button>
                  ) : null}
                </div>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
                {comment.deletedAt ? '[deleted]' : comment.body}
              </p>
            </li>
          ))}
        </ul>
      )}

      <form className="mt-4 space-y-3 border-t border-slate-200 pt-4" onSubmit={handleSubmit}>
        <TextAreaField
          label="Add a comment"
          required
          rows={3}
          value={body}
          onChange={(event) => setBody(event.target.value)}
        />
        {staff ? (
          <SelectField
            label="Visibility"
            value={visibility}
            onChange={(event) => setVisibility(event.target.value as 'PUBLIC' | 'INTERNAL')}
          >
            <option value="PUBLIC">Public reply</option>
            <option value="INTERNAL">Internal note</option>
          </SelectField>
        ) : null}
        {createComment.isError ? <FormAlert>{createComment.error.message}</FormAlert> : null}
        <SubmitButton pending={createComment.isPending}>Post comment</SubmitButton>
      </form>
    </Card>
  )
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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!ticket.data) return
    updateTicket.mutate(
      {
        title,
        description,
        category: category.trim() || null,
        version: ticket.data.version,
      },
      { onSuccess: () => setEditing(false) },
    )
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
            {current.resolutionNote ? (
              <div>
                <dt className="text-xs uppercase tracking-wide text-slate-400">Resolution note</dt>
                <dd className="text-slate-700">{current.resolutionNote}</dd>
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
            Version {current.version} · {current.source} · reopen count {current.reopenCount}
          </p>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <TransitionPanel ticket={current} />
        <AssignmentPanel ticket={current} />
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
              {updateTicket.isError ? <FormAlert>{updateTicket.error.message}</FormAlert> : null}
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

      <CommentList ticket={current} />
    </div>
  )
}
