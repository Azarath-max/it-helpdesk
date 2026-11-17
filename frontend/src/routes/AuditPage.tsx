import { useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, FormAlert, TextField } from '../components/ui'
import { api } from '../lib/api'
import { toApiError } from '../lib/apiError'
import type { components } from '../types/api'
import { useQuery } from '@tanstack/react-query'

type AuditPage = components['schemas']['Page_AuditEventRead_']

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function AuditPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const action = searchParams.get('action') ?? ''
  const entityType = searchParams.get('entityType') ?? ''
  const page = Number(searchParams.get('page') ?? '1') || 1
  const [actionInput, setActionInput] = useState(action)
  const [entityInput, setEntityInput] = useState(entityType)

  const query = useQuery({
    queryKey: ['audit', { action, entityType, page }],
    queryFn: async (): Promise<AuditPage> => {
      const { data, error, response } = await api.GET('/api/audit-events', {
        params: {
          query: {
            action: action || undefined,
            entityType: entityType || undefined,
            page,
            pageSize: 25,
          },
        },
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data
    },
  })

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const params = new URLSearchParams(searchParams)
    if (actionInput) params.set('action', actionInput)
    else params.delete('action')
    if (entityInput) params.set('entityType', entityInput)
    else params.delete('entityType')
    params.delete('page')
    setSearchParams(params)
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-slate-500">Admin</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Audit log
        </h1>
        <p className="text-sm text-slate-600">
          Append-only record of ticket and account changes.
        </p>
      </div>

      <Card>
        <form className="flex flex-wrap items-end gap-3" onSubmit={applyFilters}>
          <div className="min-w-[12rem] flex-1">
            <TextField
              label="Action"
              value={actionInput}
              onChange={(event) => setActionInput(event.target.value)}
              placeholder="ticket.created"
            />
          </div>
          <div className="min-w-[12rem] flex-1">
            <TextField
              label="Entity type"
              value={entityInput}
              onChange={(event) => setEntityInput(event.target.value)}
              placeholder="ticket"
            />
          </div>
          <button
            type="submit"
            className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
          >
            Filter
          </button>
        </form>
      </Card>

      {query.isPending ? (
        <p className="py-10 text-center text-sm text-slate-500">Loading audit events…</p>
      ) : query.isError ? (
        <FormAlert>{query.error.message}</FormAlert>
      ) : query.data.items.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-600">No audit events match the filters.</p>
        </Card>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th scope="col" className="px-5 py-3 font-medium">When</th>
                    <th scope="col" className="px-5 py-3 font-medium">Actor</th>
                    <th scope="col" className="px-5 py-3 font-medium">Action</th>
                    <th scope="col" className="px-5 py-3 font-medium">Entity</th>
                    <th scope="col" className="px-5 py-3 font-medium">Changes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {query.data.items.map((event) => (
                    <tr key={event.id}>
                      <td className="px-5 py-3 text-slate-600">{formatDate(event.createdAt)}</td>
                      <td className="px-5 py-3 text-slate-600">
                        {event.actor?.name ?? event.actorType}
                      </td>
                      <td className="px-5 py-3 font-medium text-slate-900">{event.action}</td>
                      <td className="px-5 py-3 text-slate-600">
                        {event.entityType} · {event.entityId.slice(0, 8)}
                      </td>
                      <td className="px-5 py-3 text-xs text-slate-500">
                        {event.after ? Object.keys(event.after).join(', ') : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="flex items-center justify-between text-sm text-slate-600">
            <p>
              {query.data.total} total · page {query.data.page}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => {
                  const params = new URLSearchParams(searchParams)
                  params.set('page', String(page - 1))
                  setSearchParams(params)
                }}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={page * query.data.pageSize >= query.data.total}
                onClick={() => {
                  const params = new URLSearchParams(searchParams)
                  params.set('page', String(page + 1))
                  setSearchParams(params)
                }}
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
