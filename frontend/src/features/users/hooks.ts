import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { toApiError } from '../../lib/apiError'

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
