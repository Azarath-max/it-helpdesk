import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Card, FormAlert, SubmitButton, TextField } from '../components/ui'
import { useForgotPassword } from '../features/auth/hooks'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const forgotPassword = useForgotPassword()

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    forgotPassword.mutate({ email })
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Reset your password
        </h1>
        <p className="text-sm text-slate-600">
          We will send a single-use link if the address belongs to an account.
        </p>
      </div>

      <Card>
        {forgotPassword.isSuccess ? (
          <div className="space-y-4">
            <FormAlert tone="success">
              If an account exists for that email, a reset link has been created.
            </FormAlert>
            <p className="text-sm text-slate-600">
              In local development the link is written to the API logs, and email delivery
              arrives with the notification worker.
            </p>
            <Link
              to="/login"
              className="inline-flex w-full items-center justify-center rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              Back to sign in
            </Link>
          </div>
        ) : (
          <form className="space-y-4" onSubmit={handleSubmit}>
            <TextField
              label="Email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            {forgotPassword.isError ? (
              <FormAlert>{forgotPassword.error.message}</FormAlert>
            ) : null}
            <SubmitButton pending={forgotPassword.isPending}>Create reset link</SubmitButton>
          </form>
        )}
      </Card>

      <p className="text-center text-sm text-slate-600">
        <Link to="/login" className="text-slate-500 hover:text-slate-900">
          Back to sign in
        </Link>
      </p>
    </div>
  )
}
