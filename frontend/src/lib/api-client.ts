const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
  if (token) {
    if (typeof window !== 'undefined') localStorage.setItem('fixit_token', token)
  } else {
    if (typeof window !== 'undefined') localStorage.removeItem('fixit_token')
  }
}

export function getAccessToken(): string | null {
  if (accessToken) return accessToken
  if (typeof window !== 'undefined') {
    accessToken = localStorage.getItem('fixit_token')
  }
  return accessToken
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options?: { params?: Record<string, string | number | boolean | undefined> }
): Promise<T> {
  const token = getAccessToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  let url = `${API_BASE}${path}`
  if (options?.params) {
    const searchParams = new URLSearchParams()
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        searchParams.set(key, String(value))
      }
    })
    const qs = searchParams.toString()
    if (qs) url += `?${qs}`
  }

  const res = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    setAccessToken(null)
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
    throw new Error('Sesión expirada')
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Error del servidor' }))
    throw new Error(error.detail || `Error ${res.status}`)
  }

  return res.json()
}

export const api = {
  get: <T>(path: string, params?: Record<string, string | number | boolean | undefined>) =>
    request<T>('GET', path, undefined, { params }),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),
}
