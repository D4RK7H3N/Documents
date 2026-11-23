import { createContext, useContext, useEffect, useState } from 'react'

const LoadingContext = createContext({ isLoading: false })

let activeRequests = 0
let manualTriggers = 0
let manualMessage = ''
const listeners = new Set()

function emit() {
  const isLoading = activeRequests > 0 || manualTriggers > 0
  listeners.forEach((listener) => listener(isLoading, manualMessage))
}

// Called from axios interceptors (module-level, no React needed)
export const startRequestLoading = () => {
  activeRequests += 1
  emit()
}

export const endRequestLoading = () => {
  activeRequests = Math.max(0, activeRequests - 1)
  emit()
}

// Manual triggers for non-API loading (lazy routes, auth checks, etc.).
// A message switches the screen on immediately and says what is happening -
// used by long jobs such as importing a big enrollment sheet.
export const startGlobalLoading = (message = '') => {
  manualTriggers += 1
  if (message) manualMessage = message
  emit()
}

export const stopGlobalLoading = () => {
  manualTriggers = Math.max(0, manualTriggers - 1)
  if (manualTriggers === 0) manualMessage = ''
  emit()
}

// Changes the message while the screen is already up - a long job such as an
// import reports its progress this way. Ignored when nothing is showing.
export const updateGlobalLoading = (message) => {
  if (manualTriggers === 0 || !message) return
  manualMessage = message
  emit()
}

export function LoadingProvider({ children }) {
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('')

  useEffect(() => {
    const listener = (loading, message) => {
      setIsLoading(loading)
      setLoadingMessage(message || '')
    }
    listeners.add(listener)
    return () => listeners.delete(listener)
  }, [])

  return (
    <LoadingContext.Provider value={{ isLoading, loadingMessage }}>
      {children}
    </LoadingContext.Provider>
  )
}

export function useLoading() {
  return useContext(LoadingContext)
}
