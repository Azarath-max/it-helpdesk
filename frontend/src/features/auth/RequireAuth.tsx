import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { FormAlert } from '../../components/ui'
import { useSession } from './hooks'

export function RequireAuth() {
  const session = useSession()
  const location = useLocation()

  if (session.isPending) {
    return (
      <p className="py-16 text-center text-sm text-slate-500">Checking your session…</p>
    )
  }

  if (session.isError) {
    return (
      <div className="mx-auto max-w-md py-16">
        <FormAlert>Could not verify your session. {session.error.message}</FormAlert>
      </div>
    )
  }

  if (!session.data) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
