import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-md space-y-3 py-16 text-center">
      <p className="text-sm font-medium text-slate-500">404</p>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Page not found</h1>
      <p className="text-sm text-slate-600">
        The page you are looking for does not exist in this helpdesk.
      </p>
      <Link
        to="/"
        className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
      >
        Back to overview
      </Link>
    </div>
  )
}
