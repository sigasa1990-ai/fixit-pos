import { create } from 'zustand'
import type { CartItem, Order, Payment } from '@/types'

interface CartState {
  orders: Order[]
  active_order_id: string | null
  selected_payment: Payment[]

  getActiveOrder: () => Order | undefined
  createOrder: () => string
  switchOrder: (order_id: string) => void
  closeOrder: (order_id: string) => void
  clearActiveOrder: () => void

  addItem: (item: CartItem) => void
  updateItemQuantity: (product_id: string, quantity: number) => void
  removeItem: (product_id: string) => void
  setCustomer: (customer_id: string, customer_name: string) => void
  setNotes: (notes: string) => void

  getOrderTotal: (order_id?: string) => number
  getOrderItemCount: (order_id?: string) => number

  setPayments: (payments: Payment[]) => void
  clearPayments: () => void
}

function generateOrderId(): string {
  return `ord_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`
}

function calculateItemTotals(item: CartItem): CartItem {
  const subtotal = item.unit_price * item.quantity
  const after_discount = subtotal - item.discount
  const tax = after_discount * (item.tax_rate / 100)
  return {
    ...item,
    subtotal: Math.round(subtotal * 100) / 100,
    total: Math.round((after_discount + tax) * 100) / 100,
  }
}

export const useCartStore = create<CartState>((set, get) => ({
  orders: [],
  active_order_id: null,
  selected_payment: [],

  getActiveOrder: () => {
    const state = get()
    return state.orders.find(o => o.id === state.active_order_id)
  },

  createOrder: () => {
    const state = get()
    const new_id = generateOrderId()
    const new_order: Order = {
      id: new_id,
      items: [],
      customer_id: null,
      customer_name: null,
      notes: null,
      created_at: new Date().toISOString(),
    }
    set({
      orders: [...state.orders, new_order],
      active_order_id: new_id,
    })
    return new_id
  },

  switchOrder: (order_id: string) => {
    set({ active_order_id: order_id })
  },

  closeOrder: (order_id: string) => {
    const state = get()
    const remaining = state.orders.filter(o => o.id !== order_id)
    const new_active = remaining.length > 0
      ? remaining[remaining.length - 1].id
      : null
    set({ orders: remaining, active_order_id: new_active })
  },

  clearActiveOrder: () => {
    const state = get()
    set({
      orders: state.orders.map(o =>
        o.id === state.active_order_id
          ? { ...o, items: [], customer_id: null, customer_name: null, notes: null }
          : o
      ),
    })
  },

  addItem: (item: CartItem) => {
    const state = get()
    const order = state.orders.find(o => o.id === state.active_order_id)
    if (!order) return

    const existing = order.items.find(i => i.product_id === item.product_id)
    let updated_items: CartItem[]

    if (existing) {
      updated_items = order.items.map(i =>
        i.product_id === item.product_id
          ? calculateItemTotals({ ...i, quantity: i.quantity + item.quantity })
          : i
      )
    } else {
      updated_items = [...order.items, calculateItemTotals(item)]
    }

    set({
      orders: state.orders.map(o =>
        o.id === state.active_order_id ? { ...o, items: updated_items } : o
      ),
    })
  },

  updateItemQuantity: (product_id: string, quantity: number) => {
    if (quantity <= 0) {
      get().removeItem(product_id)
      return
    }
    const state = get()
    set({
      orders: state.orders.map(o =>
        o.id === state.active_order_id
          ? {
              ...o,
              items: o.items.map(i =>
                i.product_id === product_id
                  ? calculateItemTotals({ ...i, quantity })
                  : i
              ),
            }
          : o
      ),
    })
  },

  removeItem: (product_id: string) => {
    const state = get()
    set({
      orders: state.orders.map(o =>
        o.id === state.active_order_id
          ? { ...o, items: o.items.filter(i => i.product_id !== product_id) }
          : o
      ),
    })
  },

  setCustomer: (customer_id: string, customer_name: string) => {
    const state = get()
    set({
      orders: state.orders.map(o =>
        o.id === state.active_order_id ? { ...o, customer_id, customer_name } : o
      ),
    })
  },

  setNotes: (notes: string) => {
    const state = get()
    set({
      orders: state.orders.map(o =>
        o.id === state.active_order_id ? { ...o, notes } : o
      ),
    })
  },

  getOrderTotal: (order_id?: string) => {
    const state = get()
    const order = state.orders.find(o => o.id === (order_id || state.active_order_id))
    if (!order) return 0
    return order.items.reduce((sum, i) => sum + i.total, 0)
  },

  getOrderItemCount: (order_id?: string) => {
    const state = get()
    const order = state.orders.find(o => o.id === (order_id || state.active_order_id))
    if (!order) return 0
    return order.items.reduce((sum, i) => sum + i.quantity, 0)
  },

  setPayments: (payments: Payment[]) => {
    set({ selected_payment: payments })
  },

  clearPayments: () => {
    set({ selected_payment: [] })
  },
}))
