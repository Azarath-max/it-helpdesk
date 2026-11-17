import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Card,
  FormAlert,
  SelectField,
  SubmitButton,
  TextField,
} from '../components/ui'
import { useTickets } from '../features/tickets/hooks'
import type { TicketFilters, TicketPriority, TicketStatus } from '../features/tickets/hooks'
import {
  priorityLabels,
  statusLabels,
} from '../features/tickets/status'

const statusOptions: Array<{ value: TicketStatus | ''; label: string }> = [
  { value: '', label: 'All statuses' },
  ...Object.entries(statusLabels).map(([value, label]) => ({
    value: value as TicketStatus,
    label,
  })),
]

const priorityOptions: Array<{ value: TicketPriority | ''; label: string }> = [
  { value: '', label: 'All priorities' },
  ...Object.entries(priorityLabels).map(([value, label]) => ({
    value: value as TicketPriority,
    label,
  })),
]

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function TicketsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const status = (searchParams.get('status') ?? '') as TicketStatus | ''
  const priority = (searchParams.get('priority') ?? '') as TicketPriority | ''
  const q = searchParams.get('q') ?? ''
  const page = Number(searchParams.get('page') ?? '1') || 1
  const [search, setSearch] = useState(q)

  const filters: TicketFilters = {
    status,
    priority,
    q,
    page,
    pageSize: 20,
  }

  const tickets = useTickets(filters)

  function updateParams(next: Partial<TicketFilters>) {
    const params = new URLSearchParams(searchParams)
    if (next.status !== undefined) {
      if (next.status) {
        params.set('status', next.status)
      } else {
        params.delete('status')
      }
    }
    if (next.priority !== undefined) {
      if (next.priority) {
        params.set('priority', next.priority)
      } else {
        params.delete('priority')
      }
    }
    if (next.q !== undefined) {
      if (next.q) {
        params.set('q', next.q)
      } else {
        params.delete('q')
      }
    }
    if (next.page !== undefined) {
      if (next.page > 1) {
        params.set('page', String(next.page))
      } else {
        params.delete('page')
      }
    }
    setSearchParams(params)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-500">Tickets</p>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Support requests
          </h1>
        </div>
        <Link
          to="/tickets/new"
          className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          New ticket
        </Link>
      </div>

      <Card>
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            updateParams({ q: search, page: 1 })
          }}
        >
          <div className="min-w-[12rem] flex-1">
            <SelectField
              label="Status"
              value={status}
              onChange={(event) =>
                updateParams({
                  status: event.target.value as TicketStatus | '',
                  page: 1,
                })
              }
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </SelectField>
          </div>
          <div className="min-w-[12rem] flex-1">
            <SelectField
              label="Priority"
              value={priority}
              onChange={(event) =>
                updateParams({
                  priority: event.target.value as TicketPriority | '',
                  page: 1,
                })
              }
            >
              {priorityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </SelectField>
          </div>
          <div className="min-w-[16rem] flex-[2]">
            <TextField
              label="Search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Title, reference, or description"
            />
          </div>
          <SubmitButton pending={false}>Search</SubmitButton>
        </form>
      </Card>

      {tickets.isPending ? (
        <p className="py-10 text-center text-sm text-slate-500">Loading tickets…</p>
      ) : tickets.isError ? (
        <FormAlert>{tickets.error.message}</FormAlert>
      ) : tickets.data.items.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-600">
            No tickets match the current filters.
          </p>
        </Card>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th scope="col" className="px-5 py-3 font-medium">Ref</th>
                    <th scope="col" className="px-5 py-3 font-medium">Title</th>
                    <th scope="col" className="px-5 py-3 font-medium">Status</th>
                    <th scope="col" className="px-5 py-3 font-medium">Priority</th>
                    <th scope="col" className="px-5 py-3 font-medium">Requester</th>
                    <th scope="col" className="px-5 py-3 font-medium">Updated</th>
                    <th scope="col" className="px-5 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {tickets.data.items.map((ticket) => (
                    <tr key={ticket.id}>
                      <td className="px-5 py-3 font-mono text-xs text-slate-600">
                        {ticket.publicRef}
                      </td>
                      <td className="px-5 py-3 font-medium text-slate-900">
                        {ticket.title}
                      </td>
                      <td className="px-5 py-3">{statusLabels[ticket.status]}</td>
                      <td className="px-5 py-3">{priorityLabels[ticket.priority]}</td>
                      <td className="px-5 py-3 text-slate-600">
                        {ticket.requester.name}
                      </td>
                      <td className="px-5 py-3 text-slate-600">
                        {formatDate(ticket.updatedAt)}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <Link
                          to={`/tickets/${ticket.id}`}
                          className="text-sm font-medium text-slate-900 hover:underline"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex items-center justify-between text-sm text-slate-600">
            <p>
              {tickets.data.total} total · page {tickets.data.page} of{' '}
              {Math.max(1, Math.ceil(tickets.data.total / tickets.data.pageSize))}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => updateParams({ page: page - 1 })}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={page * tickets.data.pageSize >= tickets.data.total}
                onClick={() => updateParams({ page: page + 1 })}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
