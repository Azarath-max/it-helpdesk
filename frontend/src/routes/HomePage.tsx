import { Link } from 'react-router-dom'
import { HealthChecks } from '../components/HealthChecks'
import { useSession } from '../features/auth/hooks'

const roadmap = [
  {
    phase: 'Phase 2',
    title: 'Tickets and audit',
    description: 'Scoped ticket CRUD, filters, and an append-only audit trail.',
  },
  {
    phase: 'Phase 3',
    title: 'Workflow and comments',
    description: 'Enforced status transitions, assignments, and internal notes.',
  },
  {
    phase: 'Phase 4',
    title: 'Email notifications',
    description: 'Transactional outbox, templates, retries, and Mailpit previews.',
  },
  {
    phase: 'Phase 5',
    title: 'Webhook and hardening',
    description: 'Signed webhook intake, admin tooling, and deployment hardening.',
  },
]

export function HomePage() {
  const session = useSession()
  const user = session.data ?? null

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <span className="inline-flex items-center rounded-full bg-slate-900/5 px-3 py-1 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-900/10">
          Phase 2 · Tickets and audit
        </span>
        <div className="max-w-2xl space-y-3">
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
            IT Helpdesk
          </h1>
          <p className="text-base leading-7 text-slate-600">
            A single-tenant ticketing system for IT support. Accounts, cookie sessions, and
            role-based access are live. Ticket features arrive in the next phases.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {session.isPending ? null : user ? (
            <Link
              to="/dashboard"
              className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
            >
              Go to dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/register"
                className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
              >
                Create account
              </Link>
              <Link
                to="/login"
                className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-white"
              >
                Sign in
              </Link>
            </>
          )}
        </div>
      </section>

      <HealthChecks />

      <section aria-labelledby="roadmap" className="space-y-3">
        <h2
          id="roadmap"
          className="text-sm font-semibold uppercase tracking-wide text-slate-500"
        >
          Roadmap
        </h2>
        <ul className="grid gap-4 sm:grid-cols-2">
          {roadmap.map((item) => (
            <li
              key={item.phase}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                {item.phase}
              </p>
              <h3 className="mt-1 text-sm font-semibold text-slate-900">{item.title}</h3>
              <p className="mt-1 text-sm leading-6 text-slate-600">{item.description}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
