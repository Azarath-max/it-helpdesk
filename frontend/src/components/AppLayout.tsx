import { Link, Outlet } from 'react-router-dom'

type NavItem =
  | { label: string; to: string; href?: undefined }
  | { label: string; href: string; to?: undefined }

const navigation: NavItem[] = [
  { label: 'Overview', to: '/' },
  { label: 'API docs', href: 'http://127.0.0.1:8000/docs' },
  { label: 'Mailpit', href: 'http://127.0.0.1:8025' },
]

export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-6 px-6 py-4">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid size-8 place-items-center rounded-lg bg-slate-900 text-sm font-bold text-white">
              IT
            </span>
            <span className="text-sm font-semibold tracking-tight">Helpdesk</span>
          </Link>
          <nav className="flex items-center gap-5 text-sm">
            {navigation.map((item) =>
              item.href !== undefined ? (
                <a
                  key={item.label}
                  href={item.href}
                  className="text-slate-600 transition hover:text-slate-900"
                >
                  {item.label}
                </a>
              ) : (
                <Link
                  key={item.label}
                  to={item.to}
                  className="font-medium text-slate-900 transition hover:text-slate-600"
                >
                  {item.label}
                </Link>
              ),
            )}
          </nav>
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
