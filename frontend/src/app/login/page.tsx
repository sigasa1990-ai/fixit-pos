'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Calculator, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const { login, is_authenticated } = useAuthStore()
  const [username, setUsername] = useState('')
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const pinRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (is_authenticated) {
      router.push('/pos')
    }
  }, [is_authenticated, router])

  const handlePinKeyPress = (digit: string) => {
    if (pin.length < 8) {
      setPin(prev => prev + digit)
    }
  }

  const handlePinDelete = () => {
    setPin(prev => prev.slice(0, -1))
  }

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!username || !pin) {
      setError('Ingrese usuario y PIN')
      return
    }
    setLoading(true)
    setError('')
    try {
      await login(username, pin)
      router.push('/pos')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión')
    } finally {
      setLoading(false)
      setPin('')
    }
  }

  const numpad_keys = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['', '0', '⌫'],
  ]

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-600 to-blue-800">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-pos-primary">
            <Calculator className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-pos-text">FIXIT POS</h1>
          <p className="mt-1 text-sm text-pos-text-secondary">
            Ingrese sus credenciales
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            type="text"
            placeholder="Usuario"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            className="text-center text-lg"
            disabled={loading}
          />

          <div className="relative">
            <Input
              ref={pinRef}
              type="password"
              placeholder="PIN"
              value={pin}
              readOnly
              className="text-center text-lg tracking-widest"
              disabled={loading}
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-md bg-red-50 p-2 text-sm text-pos-danger">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <div className="grid grid-cols-3 gap-2">
            {numpad_keys.map((row, ri) =>
              row.map((key, ki) => (
                <button
                  key={`${ri}-${ki}`}
                  type="button"
                  onClick={() => {
                    if (key === '⌫') handlePinDelete()
                    else if (key) handlePinKeyPress(key)
                  }}
                  className={`h-12 rounded-md text-lg font-semibold transition-colors
                    ${key === ''
                      ? 'invisible'
                      : key === '⌫'
                        ? 'bg-pos-surface-hover hover:bg-gray-200'
                        : 'bg-gray-100 hover:bg-gray-200'
                    }`}
                  disabled={loading}
                >
                  {key}
                </button>
              ))
            )}
          </div>

          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={loading || pin.length < 4}
          >
            {loading ? 'Ingresando...' : 'Ingresar'}
          </Button>
        </form>
      </div>
    </div>
  )
}
