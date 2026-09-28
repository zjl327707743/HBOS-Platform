import axios from 'axios'

interface FrappeMethodResponse<T> {
  message: T
}

const http = axios.create({
  baseURL: import.meta.env.VITE_FRAPPE_BASE_URL || '',
  withCredentials: true,
  headers: {
    'X-Requested-With': 'XMLHttpRequest',
  },
})

export async function callFrappeMethod<T>(
  method: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const response = await http.get<FrappeMethodResponse<T>>(
    `/api/method/${method}`,
    { params },
  )
  return response.data.message
}
