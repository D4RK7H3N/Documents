import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { configAPI, resolveAssetUrl } from '../services/api'
import { storage } from '../services/storage'

const SchoolConfigContext = createContext(null)

const DEFAULT_CONFIG = {
  school_name: 'School Management System',
  school_short_name: 'SMS',
  tagline: 'School Management System',
  logo_url: null,
  logo: null,
}

const LOCAL_HOST_RE = /^(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])$/i

/**
 * Normalise a media/logo URL so it is always safe to load on an HTTPS page.
 * - absolute http:// on a non-local host  -> upgraded to https://
 * - root-relative "/media/..."             -> resolved against the API base
 * Anything else (data:, blob:, https://) is returned untouched.
 */
function normalizeAssetUrl(value) {
  if (typeof value !== 'string' || !value) return value
  const url = value.trim()

  if (/^https?:\/\//i.test(url)) {
    try {
      const host = new URL(url).hostname
      if (url.toLowerCase().startsWith('http://') && !LOCAL_HOST_RE.test(host)) {
        return `https://${url.slice('http://'.length)}`
      }
    } catch {
      return url
    }
    return url
  }

  if (url.startsWith('/') && !url.startsWith('//')) {
    return resolveAssetUrl(url)
  }

  return url
}

function normalizeConfig(raw) {
  if (!raw || typeof raw !== 'object') return raw
  const next = { ...raw }
  for (const key of ['logo', 'logo_url', 'header_logo', 'header_logo_url']) {
    if (next[key]) next[key] = normalizeAssetUrl(next[key])
  }
  return next
}

function loadCachedConfig() {
  try {
    const cached = storage.getSync('schoolConfig')
    return cached ? normalizeConfig(JSON.parse(cached)) : DEFAULT_CONFIG
  } catch {
    return DEFAULT_CONFIG
  }
}

export function SchoolConfigProvider({ children }) {
  const [config, setConfig] = useState(loadCachedConfig)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [hasFetched, setHasFetched] = useState(false)
  const [printLogo, setPrintLogo] = useState(null)

  const fetchConfig = useCallback(async () => {
    if (hasFetched) return

    try {
      setLoading(true)
      setError(null)
      // No token gate: /api/school-config/current/ is public school-wide
      // configuration, so a logged-out or brand-new session must still be
      // able to read it. Gating on authToken meant a cold session kept the
      // defaults (no name, no logo, no print signatories) and, because
      // nothing re-triggered the effect after login, never recovered.
      const data = await configAPI.getConfig()
      const clean = normalizeConfig(data)
      setConfig(clean)
      setHasFetched(true)
      await storage.set('schoolConfig', JSON.stringify(clean))
    } catch (err) {
      setError(err)
      console.warn('School config fetch failed, using cached values')
    } finally {
      setLoading(false)
    }
  }, [hasFetched])

  const refetch = useCallback(() => {
    setHasFetched(false)
  }, [])

  const schoolName = config?.school_name || DEFAULT_CONFIG.school_name
  const schoolShortName = config?.school_short_name || DEFAULT_CONFIG.school_short_name
  const schoolLogo = config?.logo_url || config?.logo || null
  const schoolTagline = config?.tagline || DEFAULT_CONFIG.tagline
  // The academic year the school is currently in (e.g. "2026-2027"). It is
  // set in School Config, so it must never be hard-coded in a page.
  const academicYear = config?.current_academic_year || ''

  // react-to-print renders print targets into an iframe and blocks until every
  // image inside it has loaded. In Electron that iframe never becomes ready
  // when the content references an external image (react-to-print#511), so the
  // print dialog hangs on "Loading preview" forever. Inlining the logo as a
  // data URI removes the only external resource from the print content.
  // NOTE: must stay below the schoolLogo declaration it depends on.
  useEffect(() => {
    if (!schoolLogo || printLogo) return
    let cancelled = false
    // In dev the API (and its /media) is same-origin through the vite proxy.
    // The backend hands back absolute https://sms2-api... URLs when DEBUG is
    // off, and localhost is not in the production CORS allowlist, so fetch()
    // would be blocked — rewrite to the proxy's own path in dev only. The
    // deployed frontend keeps the absolute URL: its sms2-api origin IS
    // allowlisted there.
    const logoFetchUrl = (() => {
      if (!import.meta.env.DEV) return schoolLogo
      try {
        const u = new URL(schoolLogo, window.location.origin)
        return u.pathname.startsWith('/media/') ? u.pathname + u.search : schoolLogo
      } catch {
        return schoolLogo
      }
    })()
    ;(async () => {
      try {
        const res = await fetch(logoFetchUrl, { credentials: 'include' })
        if (!res.ok) return
        const blob = await res.blob()
        if (cancelled) return
        const reader = new FileReader()
        reader.onloadend = () => {
          if (!cancelled) setPrintLogo(String(reader.result))
        }
        reader.readAsDataURL(blob)
      } catch {
        /* logo is optional - printing still works without it */
      }
    })()
    return () => { cancelled = true }
  }, [schoolLogo, printLogo])

  // Always fetch on mount. The endpoint is public, so this must not depend on
  // a token existing yet - a cold session previously kept the default config
  // (empty signatories, no school name) for the whole session because the
  // token gate short-circuited and nothing re-ran this effect after login.
  useEffect(() => {
    fetchConfig()
  }, [fetchConfig])

  const updateConfig = useCallback(async (newConfig) => {
    const clean = normalizeConfig(newConfig)
    setConfig(clean)
    await storage.set('schoolConfig', JSON.stringify(clean))
  }, [])

  // Hand the branding to Electron so the next launch paints the splash with
  // the real school. No-op in the browser. printLogo is skipped deliberately:
  // it is a data: URI, far too large for the splash to load over IPC.
  useEffect(() => {
    const api = typeof window !== 'undefined' ? window.electronAPI : null
    if (!api?.cacheSplashBrand) return
    const name = config?.school_name
    const logo = config?.logo_url || config?.logo
    if (!name && !logo) return
    try {
      api.cacheSplashBrand({ schoolName: name || '', logoUrl: logo || '' })
    } catch {
      // Splash branding is cosmetic - never let it break the app.
    }
  }, [config])

  return (
    <SchoolConfigContext.Provider value={{
      config,
      loading,
      error,
      updateConfig,
      refetch,
      schoolName,
      schoolShortName,
      schoolLogo,
      // Data-URI logo for print targets - see the useEffect above.
      printLogo: printLogo || schoolLogo,
      schoolTagline,
      academicYear,
    }}>
      {children}
    </SchoolConfigContext.Provider>
  )
}

export function useSchoolConfig() {
  const context = useContext(SchoolConfigContext)
  if (!context) {
    throw new Error('useSchoolConfig must be used within a SchoolConfigProvider')
  }
  return context
}
