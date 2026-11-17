import { Card, RoleBadge } from '../components/ui'
import { useSession } from '../features/auth/hooks'
import { useUsers } from '../features/users/hooks'
import type { User } from '../features/auth/hooks'

const roleSummary: Record<User['role'], string> = {
  user: 'Create tickets for IT help and follow the ones you own.',
  agent: 'Triage, assign, and resolve tickets across the whole queue.',
  admin: 'Manage accounts and roles, and review the full audit trail.',
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function AdminAccounts() {
  const users = useUsers(true)

  return (
    <section aria-labelledby="accounts" className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 id="accounts" className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Accounts
        </h2>
        {users.data ? (
          <p className="text-xs text-slate-400">{users.data.total} total</p>
        ) : null}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {users.isPending ? (
          <p className="px-5 py-6 text-sm text-slate-500">Loading accounts…</p>
        ) : users.isError ? (
          <p className="px-5 py-6 text-sm text-rose-700">
            Could not load accounts. {users.error.message}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th scope="col" className="px-5 py-3 font-medium">
                    Name
                  </th>
                  <th scope="col" className="px-5 py-3 font-medium">
                    Email
                  </th>
                  <th scope="col" className="px-5 py-3 font-medium">
                    Role
                  </th>
                  <th scope="col" className="px-5 py-3 font-medium">
                    Status
                  </th>
                  <th scope="col" className="px-5 py-3 font-medium">
                    Joined
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.data.items.map((account) => (
                  <tr key={account.id}>
                    <td className="px-5 py-3 font-medium text-slate-900">{account.name}</td>
                    <td className="px-5 py-3 text-slate-600">{account.email}</td>
                    <td className="px-5 py-3">
                      <RoleBadge role={account.role} />
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={
                          account.isActive
                            ? 'text-emerald-700'
                            : 'text-slate-400'
                        }
                      >
                        {account.isActive ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-600">
                      {formatDate(account.createdAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}

export function DashboardPage() {
  const { data: user } = useSession()

  if (!user) {
    return null
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-sm font-medium text-slate-500">Dashboard</p>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Welcome, {user.name}
          </h1>
          <p className="text-sm text-slate-600">
            Signed in as {user.email}
          </p>
        </div>
        <RoleBadge role={user.role} />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Account</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Email</dt>
              <dd className="text-slate-700">{user.email}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Member since</dt>
              <dd className="text-slate-700">{formatDate(user.createdAt)}</dd>
            </div>
          </dl>
        </Card>

        <Card>
          <h2 className="text-sm font-semibold text-slate-900">Session</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            You are signed in with an opaque HttpOnly cookie. Logging out or resetting your
            password revokes the session immediately.
          </p>
        </Card>

        <Card>
          <h2 className="text-sm font-semibold text-slate-900">What you can do</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">{roleSummary[user.role]}</p>
        </Card>
      </div>

      {user.role === 'admin' ? <AdminAccounts /> : null}

      <section className="rounded-xl border border-dashed border-slate-300 bg-white/60 p-6">
        <h2 className="text-sm font-semibold text-slate-900">Next: tickets</h2>
        <p className="mt-1 text-sm text-slate-600">
          Phase 2 adds scoped ticket creation, lists, filters, and the audit trail. Your
          account and role are already enforced on the server.
        </p>
      </section>
    </div>
  )
}
