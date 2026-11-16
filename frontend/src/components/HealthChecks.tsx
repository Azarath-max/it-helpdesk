import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

function StatusPill({ state }: { state: 'ok' | 'ready' | 'down' | 'checking' }) {
  const styles: Record<typeof state, string> = {
    ok: 'bg-emerald-100 text-emerald-800 ring-emerald-600/20',
    ready: 'bg-emerald-100 text-emerald-800 ring-emerald-600/20',
    down: 'bg-rose-100 text-rose-800 ring-rose-600/20',
    checking: 'bg-slate-100 text-slate-600 ring-slate-500/20',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${styles[state]}`}
    >
      <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
      {state}
    </span>
  )
}

function CheckCard({
  title,
  description,
  endpoint,
}: {
  title: string
  description: string
  endpoint: '/health' | '/ready'
}) {
  const query = useQuery({
    queryKey: ['system', endpoint],
    queryFn: async () => {
      const { data, error, response } = await api.GET(endpoint)
      if (error || !response.ok) {
        throw new Error(`Request failed with status ${response.status}`)
      }
      return data
    },
    refetchInterval: 10_000,
    retry: false,
  })

  const state = query.isPending ? 'checking' : query.isError ? 'down' : 'ok'

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        </div>
        <StatusPill state={state} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <dt className="text-slate-500">Endpoint</dt>
        <dd className="font-mono text-slate-700">{endpoint}</dd>
        <dt className="text-slate-500">Response</dt>
        <dd className="font-mono text-slate-700">
          {query.data ? JSON.stringify(query.data) : '—'}
        </dd>
        <dt className="text-slate-500">Checked</dt>
        <dd className="text-slate-700">
          {query.dataUpdatedAt ? new Date(query.dataUpdatedAt).toLocaleTimeString() : '—'}
        </dd>
      </dl>
    </div>
  )
}

export function HealthChecks() {
  return (
    <section aria-labelledby="system-health" className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 id="system-health" className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          System health
        </h2>
        <p className="text-xs text-slate-400">Refreshes every 10 seconds</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <CheckCard
          title="Liveness"
          description="The API process is running."
          endpoint="/health"
        />
        <CheckCard
          title="Readiness"
          description="The API can reach PostgreSQL."
          endpoint="/ready"
        />
      </div>
    </section>
  )
}
