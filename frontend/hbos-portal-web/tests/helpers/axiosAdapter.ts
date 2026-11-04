import type { AxiosStatic, CreateAxiosDefaults, InternalAxiosRequestConfig } from 'axios'

interface TrackedTransport {
  get: (url: string, config: InternalAxiosRequestConfig) => unknown
  post: (url: string, data: unknown, config: InternalAxiosRequestConfig) => unknown
}

/** Keep Axios request/response interceptors real; replace only network I/O. */
export function createTrackedAxios(axios: AxiosStatic, transport: TrackedTransport, options?: CreateAxiosDefaults) {
  return axios.create({
    ...options,
    adapter: async config => {
      try {
        const result = await (config.method === 'get'
          ? transport.get(String(config.url), config)
          : config.method === 'post'
            ? transport.post(String(config.url), config.data, config)
            : Promise.reject(new Error(`Unexpected fixture method: ${config.method}`))) as { data: unknown }
        return { data: result.data, status: 200, statusText: 'OK', headers: {}, config }
      } catch (error) {
        if (error && typeof error === 'object') Object.assign(error, { config })
        throw error
      }
    },
  })
}
