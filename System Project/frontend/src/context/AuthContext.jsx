import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '../services/api'
import { storage } from '../services/storage'

const AuthContext = createContext(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

const enrichUser = (userData) => ({
  ...userData,
  // Profile name arrives as snake_case from the API; mirror it in camelCase
  // so components can rely on user.firstName / user.lastName.
  firstName: userData.firstName || userData.first_name || '',
  lastName: userData.lastName || userData.last_name || '',
  isSuperuser: !!userData.isSuperuser,
  isAdmin: !!userData.isSuperuser,
  role: userData.isSuperuser ? 'admin' : (userData.isStaff || userData.is_staff ? 'staff' : 'user'),
})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const storedUser = await storage.get('user')
      const token = await storage.get('authToken')

      if (storedUser && token) {
        try {
          if (!cancelled) setUser(enrichUser(JSON.parse(storedUser)))
        } catch {
          await storage.remove('authToken')
          await storage.remove('user')
        }
      }
      if (!cancelled) setLoading(false)
    })()
    return () => { cancelled = true }
  }, [])

  const login = async (username, password) => {
    try {
      const response = await authAPI.login(username, password)
      const { token, user: userData } = response.data

      await storage.set('authToken', token)

      const enriched = enrichUser(userData)
      await storage.set('user', JSON.stringify(enriched))
      setUser(enriched)

      return { success: true, user: enriched }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || error.response?.data?.detail || 'Login failed',
      }
    }
  }

  const logout = async () => {
    await authAPI.logout()
    setUser(null)

    const isFile = window.location.protocol === 'file:'
    window.location.href = isFile
      ? window.location.pathname + '#/login'
      : '#/login'
  }

  const updateProfile = async (profileData) => {
    try {
      const data = await authAPI.updateProfile(profileData)
      const updatedUser = {
        ...user,
        firstName: data.first_name || user.firstName,
        lastName: data.last_name || user.lastName,
        email: data.email || user.email,
        avatar: data.avatar !== undefined ? data.avatar : user.avatar,
        hasSeenOnboarding: data.has_seen_onboarding !== undefined ? data.has_seen_onboarding : user.hasSeenOnboarding,
      }
      const enriched = enrichUser(updatedUser)
      setUser(enriched)
      await storage.set('user', JSON.stringify(enriched))
      return { success: true, data }
    } catch (error) {
      return { success: false, error: error.message }
    }
  }

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      login,
      logout,
      updateProfile,
      loading,
    }}>
      {children}
    </AuthContext.Provider>
  )
}
