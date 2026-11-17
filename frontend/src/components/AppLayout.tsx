import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useLogout, useSession } from '../features/auth/hooks'
import { RoleBadge } from './ui'

function navLinkClass({ isActive }: { isActive: boolean }) {
  return isActive
    ? 'font-medium text-slate-900'
    : 'text-slate-600 transition hover:text-slate-900'
}

export function AppLayout() {
  const session = useSession()
  const logout = useLogout()
  const navigate = useNavigate()
  const user = session.data ?? null

  function handleLogout() {
    logout.mutate(undefined, { onSuccess: () => navigate('/login', { replace: true }) })
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-3 px-6 py-4">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-lg bg-slate-900 text-sm font-bold text-white">
              IT
            </span>
            <span className="text-sm font-semibold tracking-tight">Helpdesk</span>
          </Link>

          <nav className="order-3 flex w-full items-center gap-5 text-sm sm:order-none sm:w-auto">
            <NavLink to="/" end className={navLinkClass}>
              Overview
            </NavLink>
            {user ? (
              <>
                <NavLink to="/dashboard" className={navLinkClass}>
                  Dashboard
                </NavLink>
                <NavLink to="/tickets" className={navLinkClass}>
                  Tickets
                </NavLink>
              </>
            ) : null}
            <a
              href="http://127.0.0.1:8000/docs"
              className="text-slate-600 transition hover:text-slate-900"
            >
              API docs
            </a>
            <a
              href="http://127.0.0.1:8025"
              className="text-slate-600 transition hover:text-slate-900"
            >
              Mailpit
            </a>
          </nav>

          <div className="flex items-center gap-3 text-sm">
            {session.isPending ? null : user ? (
              <>
                <span className="hidden text-xs text-slate-500 md:block">{user.email}</span>
                <RoleBadge role={user.role} />
                <button
                  type="button"
                  onClick={handleLogout}
                  disabled={logout.isPending}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-slate-600 transition hover:text-slate-900"
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-slate-700"
                >
                  Create account
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-1 px-6 py-5 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>IT Helpdesk · portfolio project</p>
          <p>FastAPI · PostgreSQL · React · Tailwind CSS</p>
        </div>
      </footer>
    </div>
  )
}
