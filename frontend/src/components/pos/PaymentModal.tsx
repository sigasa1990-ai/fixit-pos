'use client'

import { useState } from 'react'
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useCartStore } from '@/stores/cart-store'
import { formatCurrency } from '@/lib/utils'
import { api } from '@/lib/api-client'
import { DollarSign, CreditCard, Building2, Globe, Banknote } from 'lucide-react'
import toast from 'react-hot-toast'
import type { Payment, Sale } from '@/types'

interface PaymentModalProps {
  open: boolean
  onClose: () => void
  onSuccess: (sale: Sale) => void
  cash_register_id: string
  branch_id: string
}

export function PaymentModal({ open, onClose, onSuccess, cash_register_id, branch_id }: PaymentModalProps) {
  const order = useCartStore(s => s.orders.find(o => o.id === s.active_order_id))
  const { clearActiveOrder, closeOrder, active_order_id } = useCartStore()

  const total = order?.items.reduce((s, i) => s + i.total, 0) || 0
  const [payments, setPayments] = useState<Payment[]>([
    { payment_method: 'cash', currency: 'MXN', amount: total, exchange_rate: 1 },
  ])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [cash_received, setCashReceived] = useState(total)

  const payment_methods = [
    { method: 'cash' as const, label: 'Efectivo', icon: Banknote, color: 'bg-emerald-50 text-emerald-600 border-emerald-200' },
    { method: 'card' as const, label: 'Tarjeta', icon: CreditCard, color: 'bg-blue-50 text-blue-600 border-blue-200' },
    { method: 'transfer' as const, label: 'Transferencia', icon: Building2, color: 'bg-purple-50 text-purple-600 border-purple-200' },
    { method: 'usd' as const, label: 'USD', icon: Globe, color: 'bg-amber-50 text-amber-600 border-amber-200' },
  ]

  const handleMethodChange = (method: Payment['payment_method']) => {
    setPayments([{ payment_method: method, currency: method === 'usd' ? 'USD' : 'MXN', amount: total, exchange_rate: method === 'usd' ? 17.5 : 1 }])
  }

  const handlePay = async () => {
    if (!order || !active_order_id) return
    if (!cash_register_id || !branch_id) {
      setError('Caja no configurada. Seleccione una caja primero.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const sale: Sale = await api.post('/api/v1/sales', {
        branch_id,
        cash_register_id,
        customer_id: order.customer_id || undefined,
        items: order.items.map(i => ({
          product_id: i.product_id,
          location_id: i.location_id,
          quantity: i.quantity,
          unit_price: i.unit_price,
          discount: i.discount,
          tax_rate: i.tax_rate,
        })),
        payments: payments.map(p => ({
          payment_method: p.payment_method,
          currency: p.currency,
          amount: p.amount,
          exchange_rate: p.exchange_rate,
        })),
        notes: order.notes,
      })

      toast.success(`Venta ${sale.folio} realizada con éxito`)
      clearActiveOrder()
      closeOrder(active_order_id)
      onSuccess(sale)
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al procesar venta')
    } finally {
      setLoading(false)
    }
  }

  const change = payments[0]?.payment_method === 'cash' ? cash_received - total : 0

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogHeader>
        <DialogTitle>Cobrar</DialogTitle>
      </DialogHeader>

      <div className="mb-4 text-center">
        <div className="text-3xl font-bold text-pos-text">{formatCurrency(total)}</div>
        <div className="text-sm text-pos-text-secondary">Total a cobrar</div>
      </div>

      <div className="mb-4">
        <div className="mb-2 text-sm font-medium text-pos-text">Método de pago</div>
        <div className="grid grid-cols-2 gap-2">
          {payment_methods.map(({ method, label, icon: Icon, color }) => (
            <button
              key={method}
              onClick={() => handleMethodChange(method)}
              className={`flex items-center gap-2 rounded-lg border-2 p-3 text-sm font-medium transition-all
                ${payments[0]?.payment_method === method
                  ? `${color} border-current`
                  : 'border-pos-border text-pos-text-secondary hover:border-gray-300'
                }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {payments[0]?.payment_method === 'cash' && (
        <div className="mb-4">
          <label className="mb-1 text-sm font-medium text-pos-text">Efectivo recibido</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-lg font-semibold text-pos-text-secondary">$</span>
            <Input
              type="number"
              value={cash_received}
              onChange={(e) => setCashReceived(Number(e.target.value))}
              className="h-12 pl-8 text-lg font-bold text-right"
              step={0.01}
              min={total}
            />
          </div>
          {change > 0 && (
            <div className="mt-1 text-right text-sm text-pos-success">
              Cambio: {formatCurrency(change)}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="mb-3 rounded-md bg-red-50 p-2 text-sm text-pos-danger">
          {error}
        </div>
      )}

      <DialogFooter>
        <Button variant="outline" onClick={onClose} disabled={loading}>
          Cancelar
        </Button>
        <Button
          onClick={handlePay}
          size="lg"
          className="min-w-[140px]"
          disabled={loading || order?.items.length === 0}
        >
          {loading ? 'Procesando...' : `Cobrar ${formatCurrency(total)}`}
        </Button>
      </DialogFooter>
    </Dialog>
  )
}
