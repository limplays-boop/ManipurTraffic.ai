const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const API_BASE_URL = (configuredBaseUrl || 'http://localhost:8000').replace(/\/+$/, '')

export type RemoteMapState = {
  status: 'loading' | 'available' | 'empty' | 'unavailable' | 'error'
  data?: unknown
  message?: string
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw new Error(`Could not reach the API at ${API_BASE_URL}.`)
  }

  if (!response.ok) {
    const responseText = await response.text()
    const detail = responseText.trim().slice(0, 240)
    throw new ApiError(
      response.status,
      detail
        ? `HTTP ${response.status}: ${detail}`
        : `HTTP ${response.status} from ${path}.`,
    )
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new Error(`The API response from ${path} was not valid JSON.`)
  }
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })
  } catch {
    throw new Error(`Could not reach the API at ${API_BASE_URL}.`)
  }

  if (!response.ok) {
    const responseText = await response.text()
    let detail = responseText.trim().slice(0, 240)
    try {
      const payload = JSON.parse(responseText) as { detail?: unknown }
      if (typeof payload.detail === 'string') detail = payload.detail
    } catch {
      // Keep the bounded response text for non-JSON API errors.
    }
    throw new ApiError(
      response.status,
      detail ? `HTTP ${response.status}: ${detail}` : `HTTP ${response.status} from ${path}.`,
    )
  }

  try {
    return (await response.json()) as T
  } catch {
    throw new Error(`The API response from ${path} was not valid JSON.`)
  }
}
