import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { Card, FormAlert, SubmitButton, TextField } from '../components/ui'
import { useLogin, useSession } from '../features/auth/hooks'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const login = useLogin()
  const session = useSession()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  if (session.data) {
    return <Navigate to={from} replace />
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    login.mutate({ email, password })
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Welcome back</h1>
        <p className="text-sm text-slate-600">Sign in to manage support requests.</p>
      </div>

      <Card>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <TextField
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {login.isError ? <FormAlert>{login.error.message}</FormAlert> : null}
          <SubmitButton pending={login.isPending}>Sign in</SubmitButton>
        </form>

        <div className="mt-5 space-y-2 text-center text-sm text-slate-600">
          <p>
            New here?{' '}
            <Link to="/register" className="font-medium text-slate-900 hover:underline">
              Create an account
            </Link>
          </p>
          <p>
            <Link to="/forgot-password" className="text-slate-500 hover:text-slate-900">
              Forgot your password?
            </Link>
          </p>
        </div>
      </Card>
    </div>
  )
}
