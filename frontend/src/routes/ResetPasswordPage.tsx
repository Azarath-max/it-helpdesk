import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Card, FormAlert, SubmitButton, TextField } from '../components/ui'
import { useResetPassword } from '../features/auth/hooks'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [mismatch, setMismatch] = useState(false)
  const resetPassword = useResetPassword()

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password !== confirmation) {
      setMismatch(true)
      return
    }
    setMismatch(false)
    resetPassword.mutate({ token, newPassword: password })
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Choose a new password
        </h1>
        <p className="text-sm text-slate-600">
          This link can be used once. All existing sessions will be signed out.
        </p>
      </div>

      <Card>
        {resetPassword.isSuccess ? (
          <div className="space-y-4">
            <FormAlert tone="success">Your password has been updated.</FormAlert>
            <Link
              to="/login"
              className="inline-flex w-full items-center justify-center rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
            >
              Sign in
            </Link>
          </div>
        ) : (
          <form className="space-y-4" onSubmit={handleSubmit}>
            {!token ? (
              <FormAlert>This reset link is missing its token.</FormAlert>
            ) : null}
            <TextField
              label="New password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={128}
              hint="At least 12 characters."
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <TextField
              label="Confirm new password"
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              maxLength={128}
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
            />
            {mismatch ? <FormAlert>Passwords do not match.</FormAlert> : null}
            {resetPassword.isError ? (
              <FormAlert>{resetPassword.error.message}</FormAlert>
            ) : null}
            <SubmitButton pending={resetPassword.isPending}>
              Update password
            </SubmitButton>
          </form>
        )}
      </Card>
    </div>
  )
}
