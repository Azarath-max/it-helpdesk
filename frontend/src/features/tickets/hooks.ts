import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import type { components } from '../../types/api'
import { api } from '../../lib/api'
import { toApiError } from '../../lib/apiError'

export type Ticket = components['schemas']['TicketRead']
export type TicketStatus = components['schemas']['TicketStatus']
export type TicketPriority = components['schemas']['TicketPriority']
export type TicketCreateInput = components['schemas']['TicketCreate']
export type TicketUpdateInput = components['schemas']['TicketUpdate']

export type TicketFilters = {
  status?: TicketStatus | ''
  priority?: TicketPriority | ''
  q?: string
  page?: number
  pageSize?: number
}

export const ticketsQueryKey = ['tickets'] as const
export const ticketDetailKey = (id: string) => ['tickets', 'detail', id] as const

function normalizeFilters(filters: TicketFilters) {
  const query: Record<string, unknown> = {}
  if (filters.status) {
    query.status = filters.status
  }
  if (filters.priority) {
    query.priority = filters.priority
  }
  if (filters.q) {
    query.q = filters.q
  }
  if (filters.page) {
    query.page = filters.page
  }
  if (filters.pageSize) {
    query.pageSize = filters.pageSize
  }
  return query
}

export function useTickets(filters: TicketFilters = {}) {
  return useQuery({
    queryKey: [...ticketsQueryKey, 'list', filters],
    queryFn: async () => {
      const { data, error, response } = await api.GET('/api/tickets', {
        params: { query: normalizeFilters(filters) },
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data
    },
    staleTime: 15_000,
  })
}

export function useTicket(id: string) {
  return useQuery({
    queryKey: ticketDetailKey(id),
    queryFn: async () => {
      const { data, error, response } = await api.GET('/api/tickets/{ticket_id}', {
        params: { path: { ticket_id: id } },
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data
    },
  })
}

export function useCreateTicket() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: async (input: TicketCreateInput) => {
      const { data, error, response } = await api.POST('/api/tickets', {
        body: input,
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data
    },
    onSuccess: (ticket) => {
      queryClient.invalidateQueries({ queryKey: ticketsQueryKey })
      navigate(`/tickets/${ticket.id}`)
    },
  })
}

export function useUpdateTicket(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: TicketUpdateInput) => {
      const { data, error, response } = await api.PATCH('/api/tickets/{ticket_id}', {
        params: { path: { ticket_id: id } },
        body: input,
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data
    },
    onSuccess: (ticket) => {
      queryClient.setQueryData(ticketDetailKey(id), ticket)
      queryClient.invalidateQueries({ queryKey: ticketsQueryKey })
    },
  })
}
