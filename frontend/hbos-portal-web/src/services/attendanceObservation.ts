import { reactive } from 'vue'
// DEV-only metadata. Never record business rows, subjects or auth context.
export const attendanceObservation = reactive({ mounts: 0, unmounts: 0, requests: 0, completed: 0, stale: 0, permissions: 0, instance: 0, request: '', draft: '', applied: '', range: '', events: [] as string[] })
export function observeAttendance(values: Partial<Omit<typeof attendanceObservation, 'events'>>) { if (import.meta.env.DEV) Object.assign(attendanceObservation, values) }
export function observeResume(name: string) { if (import.meta.env.DEV) { attendanceObservation.events.push(`${Math.round(performance.now())}:${name}`); attendanceObservation.events.splice(0, Math.max(0, attendanceObservation.events.length - 20)) } }
