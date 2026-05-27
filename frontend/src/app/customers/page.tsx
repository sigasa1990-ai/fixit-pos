'use client'

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { useRouter } from 'next/navigation'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api-client'
import { formatDate } from '@/lib/utils'
import { Search, Users } from 'lucide-react'
import type { Customer, PaginatedResponse } from '@/types'

export default function CustomersPage() {
  const router = useRouter()
  const { is_authenticated, permissions } = useAuthStore()
  const [customers, setCustomers] = useState<Customer[]>([])
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!is_authenticated) {
      const token = localStorage.getItem('fixit_token')
      if (!token) router.push('/login')
    }
  }, [is_authenticated, router])

  useEffect(() => { search() }, [query, page])

  const search = async () => {
    setLoading(true)
    try {
      const res = await api.get<PaginatedResponse<Customer>>('/api/v1/customers/search', { query, page, page_size: 20 })
      setCustomers(res.items || [])
      setTotal(res.total || 0)
    } catch {
      setCustomers([])
    } finally {
      setLoading(false)
    }
  }

  if (!is_authenticated) return null

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-pos-text">Clientes</h1>

      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pos-text-secondary" />
          <Input
            placeholder="Buscar por nombre, teléfono o RFC..."
            value={query}
            onChange={(e) => { setQuery(e.target.value); setPage(1) }}
            className="pl-10"
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-pos-text-secondary">Cargando...</div>
          ) : customers.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-8 text-pos-text-secondary">
              <Users className="h-8 w-8" />
              <span>No se encontraron clientes</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-pos-border bg-pos-surface-hover">
                    <th className="px-4 py-3 text-left font-medium">Nombre</th>
                    <th className="px-4 py-3 text-left font-medium">Teléfono</th>
                    <th className="px-4 py-3 text-left font-medium">RFC</th>
                    <th className="px-4 py-3 text-left font-medium">Email</th>
                    <th className="px-4 py-3 text-left font-medium">Régimen</th>
                    <th className="px-4 py-3 text-right font-medium">Creado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-pos-border">
                  {customers.map((c) => (
                    <tr key={c.id} className="hover:bg-pos-surface-hover">
                      <td className="px-4 py-3 font-medium">{c.name}</td>
                      <td className="px-4 py-3 text-pos-text-secondary">{c.phone || '—'}</td>
                      <td className="px-4 py-3 font-mono text-xs">{c.rfc || '—'}</td>
                      <td className="px-4 py-3 text-pos-text-secondary">{c.email || '—'}</td>
                      <td className="px-4 py-3 text-pos-text-secondary">{c.tax_regime || '—'}</td>
                      <td className="px-4 py-3 text-right text-xs text-pos-text-secondary">{formatDate(c.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {total > 20 && (
        <div className="mt-4 flex items-center justify-between text-sm text-pos-text-secondary">
          <span>{total} clientes</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</Button>
            <Button variant="outline" size="sm" disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}>Siguiente</Button>
          </div>
        </div>
      )}
    </div>
  )
}
