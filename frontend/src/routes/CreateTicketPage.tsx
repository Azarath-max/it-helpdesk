import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  FormAlert,
  SelectField,
  SubmitButton,
  TextAreaField,
  TextField,
} from '../components/ui'
import { useCreateTicket } from '../features/tickets/hooks'
import type { TicketPriority } from '../features/tickets/hooks'
import { priorityLabels } from '../features/tickets/status'

const priorityOptions: Array<{ value: TicketPriority; label: string }> = (
  Object.entries(priorityLabels) as Array<[TicketPriority, string]>
).map(([value, label]) => ({ value, label }))

export function CreateTicketPage() {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [priority, setPriority] = useState<TicketPriority>('MEDIUM')
  const createTicket = useCreateTicket()
  const navigate = useNavigate()

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    createTicket.mutate({
      title,
      description,
      priority,
      category: category.trim() || null,
    })
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <p className="text-sm font-medium text-slate-500">Tickets</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Create a support request
        </h1>
        <p className="text-sm text-slate-600">
          Describe what you need and the IT team will pick it up.
        </p>
      </div>

      <Card>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <TextField
            label="Title"
            type="text"
            required
            minLength={3}
            maxLength={160}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <TextAreaField
            label="Description"
            required
            minLength={1}
            maxLength={5000}
            rows={6}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              label="Priority"
              value={priority}
              onChange={(event) => setPriority(event.target.value as TicketPriority)}
            >
              {priorityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </SelectField>
            <TextField
              label="Category"
              type="text"
              maxLength={60}
              hint="Optional, for example Hardware or Access."
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            />
          </div>
          {createTicket.isError ? (
            <FormAlert>{createTicket.error.message}</FormAlert>
          ) : null}
          <div className="flex gap-3">
            <SubmitButton pending={createTicket.isPending}>Create ticket</SubmitButton>
            <button
              type="button"
              onClick={() => navigate('/tickets')}
              className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </Card>
    </div>
  )
}
