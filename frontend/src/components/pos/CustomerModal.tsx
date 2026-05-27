'use client'

import { useState } from 'react'
import { Dialog, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useCartStore } from '@/stores/cart-store'
import { api } from '@/lib/api-client'
import { Search, User } from 'lucide-react'
import type { Customer } from '@/types'

interface CustomerModalProps {
  open: boolean
  onClose: () => void
}

export function CustomerModal({ open, onClose }: CustomerModalProps) {
  const { setCustomer } = useCartStore()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Customer[]>([])
  const [loading, setLoading] = useState(false)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [creating, setCreating] = useState(false)

  const search = async (q: string) => {
    if (!q.trim()) return
    setLoading(true)
    try {
      const res = await api.get<{ items: Customer[] }>('/api/v1/customers/search', { query: q })
      setResults(res.items || [])
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const selectCustomer = (customer: Customer) => {
    setCustomer(customer.id, customer.name)
    onClose()
  }

  const createQuickCustomer = async () => {
    if (!name.trim()) return
    setCreating(true)
    try {
      const res = await api.post<{ id: string }>('/api/v1/customers', { name, phone: phone || undefined })
      setCustomer(res.id, name)
      onClose()
    } catch {
      // Silencio
    } finally {
      setCreating(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogHeader>
        <DialogTitle>Cliente</DialogTitle>
      </DialogHeader>

      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pos-text-secondary" />
          <Input
            placeholder="Buscar por nombre, teléfono o RFC"
            value={query}
            onChange={(e) => { setQuery(e.target.value); search(e.target.value) }}
            className="pl-10"
          />
        </div>

        {loading && (
          <div className="mt-2 text-center text-sm text-pos-text-secondary">Buscando...</div>
        )}

        {results.length > 0 && (
          <div className="mt-2 max-h-40 overflow-y-auto rounded-md border border-pos-border">
            {results.map((customer) => (
              <button
                key={customer.id}
                onClick={() => selectCustomer(customer)}
                className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition-colors hover:bg-pos-surface-hover"
              >
                <User className="h-4 w-4 text-pos-text-secondary" />
                <div>
                  <div className="font-medium">{customer.name}</div>
                  <div className="text-xs text-pos-text-secondary">
                    {customer.phone && `${customer.phone} · `}
                    {customer.rfc || 'Sin RFC'}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-pos-border pt-4">
        <div className="mb-2 text-sm font-medium text-pos-text">Cliente rápido</div>
        <div className="flex gap-2">
          <Input
            placeholder="Nombre"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1"
          />
          <Input
            placeholder="Teléfono"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-32"
          />
          <Button onClick={createQuickCustomer} disabled={creating || !name.trim()}>
            {creating ? '...' : 'Crear'}
          </Button>
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={() => { setCustomer('', ''); onClose() }}>
          Cliente genérico
        </Button>
        <Button variant="outline" onClick={onClose}>
          Cerrar
        </Button>
      </DialogFooter>
    </Dialog>
  )
}
