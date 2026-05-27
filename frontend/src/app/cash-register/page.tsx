'use client'

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api-client'
import { formatCurrency, formatDate } from '@/lib/utils'
import toast from 'react-hot-toast'
import { Toaster } from 'react-hot-toast'
import { DollarSign, ArrowUpCircle, ArrowDownCircle } from 'lucide-react'
import type { CashRegister } from '@/types'

export default function CashRegisterPage() {
  const router = useRouter()
  const { is_authenticated } = useAuthStore()
  const [registers, setRegisters] = useState<CashRegister[]>([])
  const [selected_id, setSelectedId] = useState('')
  const [opening_balance, setOpeningBalance] = useState('500')
  const [movement_amount, setMovementAmount] = useState('')
  const [movement_desc, setMovementDesc] = useState('')
  const [loading, setLoading] = useState(false)
  const [selected_register, setSelectedRegister] = useState<CashRegister | null>(null)

  useEffect(() => {
    if (!is_authenticated) {
      const token = localStorage.getItem('fixit_token')
      if (!token) router.push('/login')
    }
    loadRegisters()
  }, [is_authenticated, router])

  const loadRegisters = async () => {
    try {
      const res = await api.get<CashRegister[]>('/api/v1/cash-registers/list')
      const items = Array.isArray(res) ? res : (res as { items?: CashRegister[] }).items || []
      setRegisters(items)
    } catch {
      setRegisters([])
    }
  }

  const handleOpen = async () => {
    if (!selected_id) return
    setLoading(true)
    try {
      await api.post('/api/v1/cash-registers/open', {
        cash_register_id: selected_id,
        opening_balance: parseFloat(opening_balance) || 0,
      })
      toast.success('Caja abierta exitosamente')
      loadRegisters()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al abrir caja')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = async () => {
    if (!selected_id) return
    setLoading(true)
    try {
      const res = await api.post<{ difference: number }>('/api/v1/cash-registers/close', {
        cash_register_id: selected_id,
      })
      const diff = res.difference
      if (Math.abs(diff) > 0.01) {
        toast.error(`Diferencia en caja: ${formatCurrency(diff)}`)
      } else {
        toast.success('Caja cerrada exitosamente')
      }
      loadRegisters()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al cerrar caja')
    } finally {
      setLoading(false)
    }
  }

  const handleMovement = async (type: 'in' | 'out') => {
    if (!selected_id || !movement_amount) return
    setLoading(true)
    try {
      await api.post('/api/v1/cash-registers/movements', {
        cash_register_id: selected_id,
        amount: parseFloat(movement_amount),
        movement_type: type,
        description: movement_desc || (type === 'in' ? 'Ingreso manual' : 'Salida manual'),
      })
      toast.success('Movimiento registrado')
      setMovementAmount('')
      setMovementDesc('')
      loadRegisters()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al registrar movimiento')
    } finally {
      setLoading(false)
    }
  }

  if (!is_authenticated) return null

  return (
    <div className="p-6">
      <Toaster position="top-right" />
      <h1 className="mb-6 text-2xl font-bold text-pos-text">Gestión de Caja</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Register selection */}
        <Card>
          <CardHeader>
            <CardTitle>Cajas</CardTitle>
          </CardHeader>
          <CardContent>
            {registers.length === 0 ? (
              <div className="py-8 text-center text-sm text-pos-text-secondary">
                No hay cajas configuradas
              </div>
            ) : (
              <div className="space-y-2">
                {registers.map((reg) => (
                  <button
                    key={reg.id}
                    onClick={() => { setSelectedId(reg.id); setSelectedRegister(reg) }}
                    className={`w-full rounded-lg border p-3 text-left transition-colors
                      ${selected_id === reg.id
                        ? 'border-pos-primary bg-blue-50'
                        : 'border-pos-border hover:bg-pos-surface-hover'
                      }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-pos-text">{reg.name}</div>
                        <div className="text-xs text-pos-text-secondary">{reg.code}</div>
                      </div>
                      <div className={`rounded-full px-2 py-0.5 text-xs font-medium
                        ${reg.status === 'open' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                        {reg.status === 'open' ? 'Abierta' : 'Cerrada'}
                      </div>
                    </div>
                    {reg.status === 'open' && (
                      <div className="mt-1 text-sm font-semibold">
                        {formatCurrency(reg.current_balance)}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Center: Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Acciones</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="mb-1 text-sm font-medium text-pos-text">Monto apertura</label>
              <Input
                type="number"
                value={opening_balance}
                onChange={(e) => setOpeningBalance(e.target.value)}
                placeholder="500"
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleOpen}
                className="flex-1"
                disabled={loading || !selected_id}
              >
                <DollarSign className="mr-1 h-4 w-4" />
                Abrir Caja
              </Button>
              <Button
                onClick={handleClose}
                variant="destructive"
                className="flex-1"
                disabled={loading || !selected_id}
              >
                Cerrar Caja
              </Button>
            </div>

            <hr className="border-pos-border" />

            <div>
              <label className="mb-1 text-sm font-medium text-pos-text">Monto</label>
              <Input
                type="number"
                value={movement_amount}
                onChange={(e) => setMovementAmount(e.target.value)}
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="mb-1 text-sm font-medium text-pos-text">Descripción</label>
              <Input
                value={movement_desc}
                onChange={(e) => setMovementDesc(e.target.value)}
                placeholder="Motivo del movimiento"
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => handleMovement('in')}
                variant="success"
                className="flex-1"
                disabled={loading || !selected_id || !movement_amount}
              >
                <ArrowUpCircle className="mr-1 h-4 w-4" />
                Entrada
              </Button>
              <Button
                onClick={() => handleMovement('out')}
                variant="destructive"
                className="flex-1"
                disabled={loading || !selected_id || !movement_amount}
              >
                <ArrowDownCircle className="mr-1 h-4 w-4" />
                Salida
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Right: Register info */}
        <Card>
          <CardHeader>
            <CardTitle>Información</CardTitle>
          </CardHeader>
          <CardContent>
            {selected_register ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-pos-text-secondary">Caja:</span>
                  <span className="font-medium">{selected_register.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-pos-text-secondary">Código:</span>
                  <span className="font-medium">{selected_register.code}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-pos-text-secondary">Sucursal:</span>
                  <span className="font-medium">{selected_register.branch_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-pos-text-secondary">Estado:</span>
                  <span className={`font-medium ${selected_register.status === 'open' ? 'text-pos-success' : 'text-pos-text-secondary'}`}>
                    {selected_register.status === 'open' ? 'Abierta' : 'Cerrada'}
                  </span>
                </div>
                {selected_register.status === 'open' && (
                  <>
                    <div className="flex justify-between border-t border-pos-border pt-2">
                      <span className="text-pos-text-secondary">Apertura:</span>
                      <span className="font-medium">{formatCurrency(selected_register.opening_balance)}</span>
                    </div>
                    <div className="flex justify-between text-base font-bold">
                      <span>Saldo actual:</span>
                      <span className="text-pos-primary">{formatCurrency(selected_register.current_balance)}</span>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="py-8 text-center text-sm text-pos-text-secondary">
                Seleccione una caja
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
