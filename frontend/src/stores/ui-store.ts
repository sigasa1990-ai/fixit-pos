import { create } from 'zustand'

interface UIState {
  sidebar_open: boolean
  payment_modal_open: boolean
  customer_modal_open: boolean
  search_focused: boolean

  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setPaymentModalOpen: (open: boolean) => void
  setCustomerModalOpen: (open: boolean) => void
  setSearchFocused: (focused: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebar_open: true,
  payment_modal_open: false,
  customer_modal_open: false,
  search_focused: false,

  toggleSidebar: () => set(s => ({ sidebar_open: !s.sidebar_open })),
  setSidebarOpen: (open) => set({ sidebar_open: open }),
  setPaymentModalOpen: (open) => set({ payment_modal_open: open }),
  setCustomerModalOpen: (open) => set({ customer_modal_open: open }),
  setSearchFocused: (focused) => set({ search_focused: focused }),
}))
