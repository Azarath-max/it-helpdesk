import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { Card, FormAlert, SubmitButton, TextField } from '../components/ui'
import { useRegister, useSession } from '../features/auth/hooks'

export function RegisterPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const register = useRegister()
  const session = useSession()

  if (session.data) {
    return <Navigate to="/dashboard" replace />
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    register.mutate({ name, email, password })
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Create an account
        </h1>
        <p className="text-sm text-slate-600">
          Request help from the IT team and follow your tickets.
        </p>
      </div>

      <Card>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <TextField
            label="Full name"
            type="text"
            autoComplete="name"
            required
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
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
            autoComplete="new-password"
            required
            minLength={12}
            maxLength={128}
            hint="At least 12 characters."
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {register.isError ? <FormAlert>{register.error.message}</FormAlert> : null}
          <SubmitButton pending={register.isPending}>Create account</SubmitButton>
        </form>

        <p className="mt-5 text-center text-sm text-slate-600">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-slate-900 hover:underline">
            Sign in
          </Link>
        </p>
      </Card>

      <p className="text-center text-xs text-slate-500">
        New accounts start as requesters. An admin can grant agent or admin access.
      </p>
    </div>
  )
}
