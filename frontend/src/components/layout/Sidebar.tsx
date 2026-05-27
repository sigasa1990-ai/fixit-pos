'use client'

import { usePathname, useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth-store'
import {
  ShoppingCart,
  Box,
  Users,
  FileText,
  ClipboardList,
  BarChart3,
  LogOut,
  Calculator,
  Settings,
} from 'lucide-react'

const menuItems = [
  { path: '/pos', label: 'POS', icon: ShoppingCart, shortcut: 'F1' },
  { path: '/cash-register', label: 'Caja', icon: Calculator, shortcut: 'F2' },
  { path: '/products', label: 'Productos', icon: Box, shortcut: 'F3' },
  { path: '/customers', label: 'Clientes', icon: Users, shortcut: 'F4' },
  { path: '/sales', label: 'Ventas', icon: ClipboardList, shortcut: 'F5' },
  { path: '/quotations', label: 'Cotizaciones', icon: FileText, shortcut: 'F6' },
  { path: '/dashboard', label: 'Dashboard', icon: BarChart3, shortcut: 'F7' },
  { path: '/settings', label: 'Hardware', icon: Settings, shortcut: 'F12' },
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { full_name, role, logout } = useAuthStore()

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-pos-border bg-white">
      <div className="flex items-center gap-2 border-b border-pos-border px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-pos-primary text-sm font-bold text-white">
          F
        </div>
        <div className="font-semibold text-pos-text">FIXIT POS</div>
      </div>

      <div className="flex items-center gap-2 border-b border-pos-border px-4 py-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-pos-surface-hover text-sm font-medium">
          {full_name?.charAt(0) || '?'}
        </div>
        <div className="text-xs">
          <div className="font-medium text-pos-text">{full_name || 'Usuario'}</div>
          <div className="capitalize text-pos-text-secondary">{role}</div>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {menuItems.map((item) => {
          const Icon = item.icon
          const is_active = pathname === item.path || pathname.startsWith(item.path + '/')
          return (
            <button
              key={item.path}
              onClick={() => router.push(item.path)}
              className={cn(
                'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                is_active
                  ? 'bg-pos-primary text-white'
                  : 'text-pos-text-secondary hover:bg-pos-surface-hover hover:text-pos-text'
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="flex-1 text-left">{item.label}</span>
              <span className="text-[10px] opacity-50">{item.shortcut}</span>
            </button>
          )
        })}
      </nav>

      <div className="border-t border-pos-border p-2">
        <button
          onClick={() => { logout(); router.push('/login') }}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-pos-text-secondary transition-colors hover:bg-pos-surface-hover hover:text-pos-danger"
        >
          <LogOut className="h-4 w-4" />
          Cerrar sesión
        </button>
      </div>
    </aside>
  )
}
