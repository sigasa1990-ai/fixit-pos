'use client'

import { useCartStore } from '@/stores/cart-store'
import { Plus, X } from 'lucide-react'

export function OrderTabs() {
  const { orders, active_order_id, createOrder, switchOrder, closeOrder } = useCartStore()

  return (
    <div className="flex items-center gap-1 border-b border-pos-border bg-white px-2">
      {orders.map((order) => (
        <div
          key={order.id}
          onClick={() => switchOrder(order.id)}
          className={`group flex cursor-pointer items-center gap-2 rounded-t-md px-3 py-2 text-sm transition-colors
            ${order.id === active_order_id
              ? 'bg-pos-background font-medium text-pos-text'
              : 'text-pos-text-secondary hover:bg-pos-surface-hover'
            }`}
        >
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-pos-primary/10 text-xs font-medium">
            {order.items.reduce((s, i) => s + i.quantity, 0)}
          </span>
          <span>Orden {orders.indexOf(order) + 1}</span>
          <span className="text-xs text-pos-text-secondary">
            ${order.items.reduce((s, i) => s + i.total, 0).toFixed(0)}
          </span>
          {orders.length > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); closeOrder(order.id) }}
              className="ml-1 rounded-full p-0.5 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-100 hover:text-red-500"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      ))}
      <button
        onClick={createOrder}
        className="flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-pos-text-secondary transition-colors hover:bg-pos-surface-hover"
        title="Nueva orden (+)"
      >
        <Plus className="h-3.5 w-3.5" />
        Nueva
      </button>
    </div>
  )
}
