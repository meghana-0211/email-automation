
import { create } from 'zustand'

interface AuthState {
  token: string | null;
  setToken: (token: string) => void;
  clearToken: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  setToken: (token) => set({ token }),
  clearToken: () => set({ token: null }),
}))

export const api = {
  async login(email: string, password: string) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!response.ok) throw new Error('Login failed')
    const data = await response.json()
    useAuthStore.getState().setToken(data.token)
    return data
  },
  
  async startCampaign(campaignData: any) {
    const token = useAuthStore.getState().token
    const response = await fetch('/api/campaign/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(campaignData),
    })
    if (!response.ok) throw new Error('Failed to start campaign')
    return await response.json()
  }
}