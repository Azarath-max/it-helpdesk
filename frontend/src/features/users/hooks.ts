import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { toApiError } from '../../lib/apiError'
import type { components } from '../../types/api'

export type UsersPage = components['schemas']['Page_UserRead_']
export type UpdateUserRoleInput = components['schemas']['UpdateUserRoleRequest']
export type UpdateUserStatusInput = components['schemas']['UpdateUserStatusRequest']

export function useUsers(enabled: boolean) {
  return useQuery({
    queryKey: ['users', { page: 1, pageSize: 50 }],
    enabled,
    queryFn: async () => {
      const { data, error, response } = await api.GET('/api/users', {
        params: { query: { page: 1, pageSize: 50 } },
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data
    },
  })
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: { userId: string; role: UpdateUserRoleInput['role'] }) => {
      const { data, error, response } = await api.PATCH('/api/users/{user_id}/role', {
        params: { path: { user_id: input.userId } },
        body: { role: input.role },
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}

export function useUpdateUserStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: { userId: string; isActive: boolean }) => {
      const { data, error, response } = await api.PATCH('/api/users/{user_id}/status', {
        params: { path: { user_id: input.userId } },
        body: { isActive: input.isActive },
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
