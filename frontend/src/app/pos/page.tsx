'use client'

import { useEffect, useCallback, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Toaster, toast } from 'react-hot-toast'
import { useAuthStore } from '@/stores/auth-store'
import { useCartStore } from '@/stores/cart-store'
import { useUIStore } from '@/stores/ui-store'
import { ProductSearch } from '@/components/pos/ProductSearch'
import { ProductGrid } from '@/components/pos/ProductGrid'
import { OrderTabs } from '@/components/pos/OrderTabs'
import { CartPanel } from '@/components/pos/CartPanel'
import { PaymentModal } from '@/components/pos/PaymentModal'
import { CustomerModal } from '@/components/pos/CustomerModal'
import { SaleComplete } from '@/components/pos/SaleComplete'
import { ShortcutHelp } from '@/components/pos/ShortcutHelp'
import { api } from '@/lib/api-client'
import { usePrinter } from '@/hooks/usePrinter'
import { useBarcodeScanner } from '@/hooks/useBarcodeScanner'
import { useKeyboard, POS_SHORTCUTS } from '@/hooks/useKeyboard'
import { Printer, Wifi, WifiOff, Keyboard, ShoppingCart, X, ScanLine } from 'lucide-react'
import type { Product, CashRegister, TicketData } from '@/types'

export default function POSPage() {
  const router = useRouter()
  const { is_authenticated, full_name, role } = useAuthStore()
  const { createOrder, active_order_id, orders, addItem, clearActiveOrder } = useCartStore()
  const { payment_modal_open, setPaymentModalOpen, customer_modal_open, setCustomerModalOpen } = useUIStore()
  const search_container_ref = useRef<HTMLDivElement>(null)
  const search_ref = useRef<HTMLInputElement>(null)

  const [branch_id, setBranchId] = useState<string>('')
  const [cash_register_id, setCashRegisterId] = useState<string>('')
  const [cash_registers, setCashRegisters] = useState<CashRegister[]>([])
  const [tenant_info, setTenantInfo] = useState<TenantInfo | null>(null)
  const [shortcut_help_open, setShortcutHelpOpen] = useState(false)
  const [last_sale, setLastSale] = useState<{ folio: string; total: number; id: string } | null>(null)
  const [scanner_feedback, setScannerFeedback] = useState(false)

  const printer = usePrinter()
  const [printer_initialized, setPrinterInitialized] = useState(false)

  // Barcode scanner
  useBarcodeScanner({
    onScan: useCallback(async (barcode: string) => {
      if (!cash_register_id) return
      setScannerFeedback(true)
      setTimeout(() => setScannerFeedback(false), 300)
      try {
        const res = await api.get<{ items: Product[] }>('/api/v1/products/search', {
          query: barcode,
          page_size: 1,
          is_active: true,
        })
        if (res.items?.[0]) {
          handleProductSelect(res.items[0])
          toast.success(`✓ ${res.items[0].name}`, { duration: 1000 })
        }
      } catch { /* ignore */ }
    }, [cash_register_id]),
  })

  // Keyboard shortcuts
  const shortcuts = [
    {
      ...POS_SHORTCUTS.SEARCH, action: () => {
        search_container_ref.current?.querySelector('input')?.focus()
      },
      enabled: () => true,
    },
    {
      ...POS_SHORTCUTS.PAY, action: () => {
        if (useCartStore.getState().orders.find(o => o.id === useCartStore.getState().active_order_id)?.items.length) {
          setPaymentModalOpen(true)
        }
      },
    },
    {
      ...POS_SHORTCUTS.CLEAR, action: () => { clearActiveOrder(); toast('Venta limpiada', { duration: 1000 }) },
    },
    {
      ...POS_SHORTCUTS.NEW_ORDER, action: () => createOrder(),
    },
    {
      ...POS_SHORTCUTS.SHORTCUT_HELP, action: () => setShortcutHelpOpen(true),
    },
  ]

  useKeyboard(shortcuts)

  // Auth check
  useEffect(() => {
    if (!is_authenticated) {
      const token = localStorage.getItem('fixit_token')
      if (!token) router.push('/login')
    }
  }, [is_authenticated, router])

  // Auto-create first order
  useEffect(() => {
    if (!active_order_id && orders.length === 0) createOrder()
  }, [active_order_id, orders.length, createOrder])

  // Load data on mount
  useEffect(() => { loadCashRegisters(); loadTenantInfo() }, [])

  // Auto-connect printer
  useEffect(() => {
    if (!printer_initialized && printer.status === 'disconnected') {
      printer.connect()
      setPrinterInitialized(true)
    }
  }, [printer_initialized, printer])

  // Listen for reprint events from SaleComplete
  useEffect(() => {
    const handler = (e: CustomEvent) => {
      const saleId = e.detail
      if (saleId && last_sale) {
        printSale(saleId)
      }
    }
    window.addEventListener('fixit-reprint', handler as EventListener)
    return () => window.removeEventListener('fixit-reprint', handler as EventListener)
  }, [last_sale])

  const loadCashRegisters = async () => {
    try {
      const res = await api.get<CashRegister[]>('/api/v1/cash-registers')
      if (Array.isArray(res)) {
        setCashRegisters(res)
        const open_reg = res.find(r => r.status === 'open')
        if (open_reg) { setCashRegisterId(open_reg.id); setBranchId(open_reg.branch_id) }
      }
    } catch { /* ignore */ }
  }

  const loadTenantInfo = async () => {
    try {
      const res = await api.get<TenantInfoRaw>('/api/v1/tenant/info')
      setTenantInfo({
        businessName: res.business_name,
        rfc: res.rfc, address: res.address, phone: res.phone,
        ticketFooter: res.ticket_footer, ticketPolicies: res.ticket_policies,
      })
    } catch { /* ignore */ }
  }

  const addProductToCart = useCallback((product: Product) => {
    if (!cash_register_id) { toast.error('Seleccione una caja primero'); return }
    addItem({
      id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}`,
      product_id: product.id,
      product_code: product.product_code,
      product_name: product.name,
      barcode: product.barcode,
      location_id: cash_register_id,
      quantity: 1,
      unit_price: product.price,
      discount: 0,
      tax_rate: product.tax_rate,
      subtotal: product.price,
      total: product.price + (product.price * product.tax_rate / 100),
    })
  }, [addItem, cash_register_id])

  const handleProductSelect = useCallback((product: Product) => {
    addProductToCart(product)
    search_ref.current?.focus()
  }, [addProductToCart])

  const printSale = useCallback(async (saleId: string) => {
    try {
      const sale = await api.get<SaleDataRaw>(`/api/v1/sales/${saleId}`)
      const ticket: TicketData = {
        businessName: tenant_info?.businessName || 'FIXIT POS',
        rfc: tenant_info?.rfc, address: tenant_info?.address, phone: tenant_info?.phone,
        folio: sale.folio, cashier: full_name || '',
        date: new Date(sale.created_at).toLocaleString('es-MX'),
        customer_name: sale.customer_name || undefined,
        items: sale.items.map(i => ({ name: i.product_name, quantity: i.quantity, price: i.unit_price, total: i.total })),
        subtotal: sale.subtotal, discount: sale.discount_total, tax: sale.tax_total, total: sale.total,
        payments: sale.payments.map(p => ({ method: p.payment_method, amount: p.amount })),
        footer: tenant_info?.ticketFooter, policies: tenant_info?.ticketPolicies,
      }
      if (printer.connected && printer.selectedPrinter) {
        await printer.printReceipt(ticket)
        if (sale.payments.some(p => p.payment_method === 'cash')) {
          await printer.openDrawer()
        }
      }
    } catch { /* ignore */ }
  }, [tenant_info, full_name, printer])

  const handleSaleSuccess = useCallback(async (saleData: { folio: string; total: number; id: string }) => {
    setLastSale(saleData)
    await printSale(saleData.id)
  }, [printSale])

  const handleNewSale = useCallback(() => {
    setLastSale(null)
    createOrder()
  }, [createOrder])

  if (!is_authenticated) return null

  return (
    <div className="flex h-full flex-col">
      <Toaster position="top-right" toastOptions={{ duration: 2000 }} />

      {/* Scanner feedback flash */}
      {scanner_feedback && (
        <div className="pointer-events-none fixed inset-0 z-40 bg-pos-primary/5 transition-all duration-150" />
      )}

      {/* Header */}
      <div className="flex items-center justify-between border-b border-pos-border bg-white px-4 py-2">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold text-pos-text flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-pos-primary" />
            POS
          </h1>
          <div className="flex items-center gap-2">
            <span className="text-xs text-pos-text-secondary">Caja:</span>
            <select
              value={cash_register_id}
              onChange={(e) => {
                const reg = cash_registers.find(r => r.id === e.target.value)
                setCashRegisterId(e.target.value)
                if (reg) setBranchId(reg.branch_id)
              }}
              className="rounded-md border border-pos-border px-2 py-1 text-xs bg-white"
            >
              <option value="">Seleccionar caja</option>
              {cash_registers.map(r => (
                <option key={r.id} value={r.id}>{r.name} ({r.status})</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-pos-text-secondary">
          {/* Scanner indicator */}
          <div className="flex items-center gap-1 rounded-md bg-pos-surface-hover px-2 py-1" title="Escáner activo">
            <ScanLine className="h-3 w-3 text-pos-success" />
            <span className="hidden sm:inline">Escáner</span>
          </div>

          {/* Printer status */}
          <button
            onClick={() => printer.status === 'disconnected' ? printer.connect() : undefined}
            className={`flex items-center gap-1 rounded-md px-2 py-1 transition-colors ${
              printer.connected ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
            }`}
            title={printer.connected ? `Impresora: ${printer.selectedPrinter}` : 'Conectar impresora'}
          >
            {printer.connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          </button>

          {/* Shortcut help */}
          <button
            onClick={() => setShortcutHelpOpen(true)}
            className="flex items-center gap-1 rounded-md px-2 py-1 transition-colors hover:bg-pos-surface-hover"
            title="Atajos de teclado (Ctrl+/)"
          >
            <Keyboard className="h-3 w-3" />
          </button>

          <span className="ml-1 hidden sm:inline">{full_name}</span>
          <span className="capitalize hidden sm:inline">· {role}</span>
        </div>
      </div>

      {/* Main POS area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Search + Product Grid */}
        <div className="flex flex-1 flex-col min-w-0">
          <div className="p-3">
            <ProductSearch onProductSelect={handleProductSelect} autoFocus={true} />
          </div>
          <div className="flex-1 overflow-y-auto px-3 pb-3 scrollbar-thin">
            <ProductGrid onProductSelect={handleProductSelect} location_id={cash_register_id} />
          </div>
        </div>

        {/* Right: Cart panel */}
        <div className="flex w-[380px] flex-shrink-0 flex-col border-l border-pos-border">
          <OrderTabs />
          <CartPanel
            onOpenCustomer={() => setCustomerModalOpen(true)}
            onOpenPayment={() => setPaymentModalOpen(true)}
          />
        </div>
      </div>

      {/* Modals */}
      <PaymentModal
        open={payment_modal_open}
        onClose={() => setPaymentModalOpen(false)}
        onSuccess={handleSaleSuccess}
        cash_register_id={cash_register_id}
        branch_id={branch_id}
      />
      <CustomerModal
        open={customer_modal_open}
        onClose={() => setCustomerModalOpen(false)}
      />
      <ShortcutHelp
        open={shortcut_help_open}
        onClose={() => setShortcutHelpOpen(false)}
      />
      <SaleComplete
        sale={last_sale}
        onNewSale={handleNewSale}
      />
    </div>
  )
}

// Types
interface TenantInfo {
  businessName: string; rfc?: string; address?: string; phone?: string;
  ticketFooter?: string; ticketPolicies?: string
}
interface TenantInfoRaw {
  business_name: string; rfc: string; address: string; phone: string;
  ticket_footer: string; ticket_policies: string
}
interface SaleDataRaw {
  folio: string; total: number; subtotal: number; discount_total: number; tax_total: number;
  user_name: string; customer_name: string | null;
  items: Array<{ product_name: string; quantity: number; unit_price: number; total: number; discount: number }>;
  payments: Array<{ payment_method: string; amount: number }>;
  created_at: string;
}
