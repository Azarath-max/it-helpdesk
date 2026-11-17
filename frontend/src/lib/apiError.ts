type ErrorEnvelope = {
  error?: {
    code?: string
    message?: string
    requestId?: string
  }
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly requestId: string | undefined

  constructor(
    message: string,
    options: { code: string; status: number; requestId?: string },
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = options.code
    this.status = options.status
    this.requestId = options.requestId
  }
}

export function toApiError(payload: unknown, status: number): ApiError {
  const error = (payload as ErrorEnvelope | undefined)?.error

  return new ApiError(error?.message ?? `Request failed with status ${status}`, {
    code: error?.code ?? 'HTTP_ERROR',
    status,
    requestId: error?.requestId,
  })
}
