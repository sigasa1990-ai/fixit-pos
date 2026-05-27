'use client'

import { useCartStore } from '@/stores/cart-store'
import { formatCurrency } from '@/lib/utils'
import { Trash2, Minus, Plus, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { Product } from '@/types'

interface CartPanelProps {
  onOpenCustomer: () => void
  onOpenPayment: () => void
}

export function CartPanel({ onOpenCustomer, onOpenPayment }: CartPanelProps) {
  const order = useCartStore(s => s.orders.find(o => o.id === s.active_order_id))
  const { updateItemQuantity, removeItem, setCustomer } = useCartStore()

  const items = order?.items || []
  const total = items.reduce((s, i) => s + i.total, 0)
  const item_count = items.reduce((s, i) => s + i.quantity, 0)

  return (
    <div className="flex h-full flex-col bg-white">
      <div className="flex items-center justify-between border-b border-pos-border px-4 py-2">
        <div className="text-sm font-medium text-pos-text">
          Carrito ({item_count} items)
        </div>
        <div className="text-xs text-pos-text-secondary">
          Total: {formatCurrency(total)}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {items.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-pos-text-secondary">
            Escanee o busque productos para comenzar
          </div>
        ) : (
          <div className="divide-y divide-pos-border">
            {items.map((item) => (
              <div key={item.product_id} className="px-4 py-2 hover:bg-pos-surface-hover">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-pos-text truncate">
                      {item.product_name}
                    </div>
                    <div className="text-xs text-pos-text-secondary">
                      {formatCurrency(item.unit_price)} c/u
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold">
                      {formatCurrency(item.total)}
                    </div>
                  </div>
                </div>

                <div className="mt-1 flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => updateItemQuantity(item.product_id, item.quantity - 1)}
                      className="flex h-7 w-7 items-center justify-center rounded-md border border-pos-border transition-colors hover:bg-pos-surface-hover"
                    >
                      <Minus className="h-3 w-3" />
                    </button>
                    <span className="flex h-7 w-10 items-center justify-center text-sm font-medium">
                      {item.quantity}
                    </span>
                    <button
                      onClick={() => updateItemQuantity(item.product_id, item.quantity + 1)}
                      className="flex h-7 w-7 items-center justify-center rounded-md border border-pos-border transition-colors hover:bg-pos-surface-hover"
                    >
                      <Plus className="h-3 w-3" />
                    </button>
                  </div>
                  <button
                    onClick={() => removeItem(item.product_id)}
                    className="flex h-7 w-7 items-center justify-center rounded-md text-pos-text-secondary transition-colors hover:bg-red-50 hover:text-pos-danger"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                {item.discount > 0 && (
                  <div className="mt-0.5 text-xs text-pos-accent">
                    Descuento: -{formatCurrency(item.discount)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-pos-border p-4">
        <div className="mb-3 space-y-1 text-sm">
          <div className="flex justify-between text-pos-text-secondary">
            <span>Subtotal</span>
            <span>{formatCurrency(items.reduce((s, i) => s + i.subtotal, 0))}</span>
          </div>
          <div className="flex justify-between text-lg font-bold text-pos-text">
            <span>Total</span>
            <span>{formatCurrency(total)}</span>
          </div>
        </div>

        <div className="flex gap-2">
          {order?.customer_name ? (
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenCustomer}
              className="flex-1 text-xs"
            >
              <User className="mr-1 h-3 w-3" />
              {order.customer_name}
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenCustomer}
              className="flex-1 text-xs"
            >
              <User className="mr-1 h-3 w-3" />
              Cliente
            </Button>
          )}
        </div>

        <Button
          onClick={onOpenPayment}
          size="xl"
          className="mt-2 w-full text-base font-bold"
          disabled={items.length === 0}
        >
          Cobrar ({formatCurrency(total)})
        </Button>

        <div className="mt-2 text-center text-[10px] text-pos-text-secondary">
          F8: Cobrar · F11: Limpiar · +: Nueva orden
        </div>
      </div>
    </div>
  )
}
