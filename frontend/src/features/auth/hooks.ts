import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { components } from '../../types/api'
import { api } from '../../lib/api'
import { toApiError } from '../../lib/apiError'

export type User = components['schemas']['UserRead']
export type LoginInput = components['schemas']['LoginRequest']
export type RegisterInput = components['schemas']['RegisterRequest']
export type ForgotPasswordInput = components['schemas']['ForgotPasswordRequest']
export type ResetPasswordInput = components['schemas']['ResetPasswordRequest']

export const sessionQueryKey = ['auth', 'session'] as const

export function useSession() {
  return useQuery<User | null>({
    queryKey: sessionQueryKey,
    queryFn: async () => {
      const { data, response } = await api.GET('/api/auth/me')

      if (response.status === 401) {
        return null
      }
      if (!response.ok || !data) {
        throw toApiError(undefined, response.status)
      }
      return data
    },
    staleTime: 30_000,
    retry: false,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: LoginInput) => {
      const { data, error, response } = await api.POST('/api/auth/login', {
        body: input,
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data.user
    },
    onSuccess: (user) => {
      queryClient.setQueryData(sessionQueryKey, user)
    },
  })
}

export function useRegister() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: RegisterInput) => {
      const { data, error, response } = await api.POST('/api/auth/register', {
        body: input,
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data.user
    },
    onSuccess: (user) => {
      queryClient.setQueryData(sessionQueryKey, user)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.POST('/api/auth/logout')
      if (!response.ok) {
        throw toApiError(error, response.status)
      }
    },
    onSuccess: () => {
      queryClient.setQueryData(sessionQueryKey, null)
      queryClient.removeQueries({ queryKey: ['users'] })
    },
  })
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: async (input: ForgotPasswordInput) => {
      const { data, error, response } = await api.POST('/api/auth/forgot-password', {
        body: input,
      })
      if (!response.ok || !data) {
        throw toApiError(error, response.status)
      }
      return data
    },
  })
}

export function useResetPassword() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (input: ResetPasswordInput) => {
      const { error, response } = await api.POST('/api/auth/reset-password', {
        body: input,
      })
      if (!response.ok) {
        throw toApiError(error, response.status)
      }
    },
    onSuccess: () => {
      // The server revoked every session, so drop any cached identity.
      queryClient.setQueryData(sessionQueryKey, null)
      queryClient.removeQueries({ queryKey: ['users'] })
    },
  })
}
