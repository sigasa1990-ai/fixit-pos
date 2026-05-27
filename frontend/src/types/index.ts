export interface User {
  id: string
  full_name: string
  role: string
  permissions: string[]
  tenant_id: string
}

export interface Product {
  id: string
  product_code: string
  barcode: string | null
  sku: string | null
  name: string
  description: string | null
  price: number
  cost: number
  min_price: number | null
  tax_rate: number
  unit: string
  warranty_days: number
  warranty_type: string
  is_active: boolean
  is_service: boolean
  track_inventory: boolean
  category_name: string | null
  created_at: string
  updated_at: string
}

export interface CartItem {
  id: string
  product_id: string
  product_code: string
  product_name: string
  barcode: string | null
  location_id: string
  quantity: number
  unit_price: number
  discount: number
  tax_rate: number
  subtotal: number
  total: number
}

export interface Order {
  id: string
  items: CartItem[]
  customer_id: string | null
  customer_name: string | null
  notes: string | null
  created_at: string
}

export interface Payment {
  payment_method: 'cash' | 'card' | 'transfer' | 'usd'
  currency: 'MXN' | 'USD'
  amount: number
  exchange_rate: number
  reference?: string
  bank?: string
  authorization_code?: string
  last_four_digits?: string
  card_type?: string
}

export interface Customer {
  id: string
  name: string
  phone: string | null
  email: string | null
  rfc: string | null
  business_name: string | null
  tax_regime: string | null
  cfdi_usage: string | null
  tax_address: string | null
  is_active: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface CashRegister {
  id: string
  branch_id: string
  location_id: string
  code: string
  name: string
  status: 'open' | 'closed'
  current_balance: number
  opening_balance: number
  branch_name: string
  location_name: string
  is_active: boolean
}

export interface Sale {
  id: string
  folio: string
  status: string
  subtotal: number
  tax_total: number
  discount_total: number
  total: number
  payment_status: string
  user_name: string
  customer_name: string | null
  created_at: string
  items?: SaleItem[]
  payments?: Payment[]
}

export interface SaleItem {
  id: string
  product_id: string
  product_name: string
  product_code: string
  quantity: number
  unit_price: number
  discount: number
  total: number
}

export interface Quotation {
  id: string
  folio: string
  status: string
  subtotal: number
  total: number
  user_name: string
  customer_name: string | null
  valid_until: string | null
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface TicketData {
  businessName: string
  rfc?: string
  address?: string
  phone?: string
  folio: string
  cashier: string
  date: string
  customer_name?: string
  items: Array<{
    name: string
    quantity: number
    price: number
    total: number
  }>
  subtotal: number
  discount: number
  tax: number
  total: number
  payments: Array<{
    method: string
    amount: number
    reference?: string
  }>
  footer?: string
  policies?: string
}
