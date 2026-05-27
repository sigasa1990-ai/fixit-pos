'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { formatCurrency } from '@/lib/utils'
import { CheckCircle, Printer, Receipt, ShoppingCart } from 'lucide-react'

interface SaleCompleteProps {
  sale: {
    folio: string
    total: number
    id: string
  } | null
  onNewSale: () => void
  autoCloseMs?: number
}

export function SaleComplete({ sale, onNewSale, autoCloseMs = 5000 }: SaleCompleteProps) {
  const [visible, setVisible] = useState(false)
  const [countdown, setCountdown] = useState(autoCloseMs / 1000)
  const router = useRouter()

  useEffect(() => {
    if (sale) {
      setVisible(true)
      setCountdown(autoCloseMs / 1000)
    }
  }, [sale, autoCloseMs])

  useEffect(() => {
    if (!visible) return
    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(interval)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    const timer = setTimeout(() => {
      setVisible(false)
      onNewSale()
    }, autoCloseMs)
    return () => {
      clearTimeout(timer)
      clearInterval(interval)
    }
  }, [visible, autoCloseMs, onNewSale])

  if (!visible || !sale) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 text-center shadow-2xl animate-in zoom-in-95">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
          <CheckCircle className="h-8 w-8 text-emerald-600" />
        </div>

        <h2 className="mb-1 text-xl font-bold text-pos-text">Venta Completada</h2>
        <p className="mb-1 text-3xl font-bold text-pos-primary">{formatCurrency(sale.total)}</p>
        <p className="mb-6 text-sm text-pos-text-secondary">Folio: {sale.folio}</p>

        <div className="space-y-2">
          <Button
            onClick={() => {
              // Re-print via the print hook
              window.dispatchEvent(new CustomEvent('fixit-reprint', { detail: sale.id }))
            }}
            className="w-full"
            size="lg"
          >
            <Printer className="mr-2 h-5 w-5" />
            Reimprimir ticket
          </Button>

          <Button
            onClick={() => router.push(`/sales/${sale.id}`)}
            variant="outline"
            className="w-full"
            size="lg"
          >
            <Receipt className="mr-2 h-5 w-5" />
            Ver detalle de venta
          </Button>

          <Button
            onClick={() => { setVisible(false); onNewSale() }}
            variant="secondary"
            className="w-full"
            size="lg"
          >
            <ShoppingCart className="mr-2 h-5 w-5" />
            Nueva venta ({countdown}s)
          </Button>
        </div>
      </div>
    </div>
  )
}
