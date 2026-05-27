'use client'

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { useRouter } from 'next/navigation'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api-client'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Search, ClipboardList, Receipt } from 'lucide-react'
import type { Sale, PaginatedResponse } from '@/types'

export default function SalesPage() {
  const router = useRouter()
  const { is_authenticated } = useAuthStore()
  const [sales, setSales] = useState<Sale[]>([])
  const [folio, setFolio] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!is_authenticated) {
      const token = localStorage.getItem('fixit_token')
      if (!token) router.push('/login')
    }
  }, [is_authenticated, router])

  useEffect(() => { search() }, [page])

  const search = async () => {
    setLoading(true)
    try {
      const res = await api.get<PaginatedResponse<Sale>>('/api/v1/sales/search', { folio, page, page_size: 20 })
      setSales(res.items || [])
      setTotal(res.total || 0)
    } catch {
      setSales([])
    } finally {
      setLoading(false)
    }
  }

  const status_variant = (status: string) => {
    if (status === 'completed') return 'success' as const
    if (status === 'cancelled') return 'danger' as const
    return 'warning' as const
  }

  if (!is_authenticated) return null

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-pos-text">Ventas</h1>
      </div>

      <div className="mb-4 flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pos-text-secondary" />
          <Input
            placeholder="Buscar por folio..."
            value={folio}
            onChange={(e) => setFolio(e.target.value)}
            className="pl-10"
            onKeyDown={(e) => e.key === 'Enter' && search()}
          />
        </div>
        <Button onClick={search}>Buscar</Button>
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-pos-text-secondary">Cargando...</div>
          ) : sales.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-8 text-pos-text-secondary">
              <Receipt className="h-8 w-8" />
              <span>No se encontraron ventas</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-pos-border bg-pos-surface-hover">
                    <th className="px-4 py-3 text-left font-medium">Folio</th>
                    <th className="px-4 py-3 text-left font-medium">Usuario</th>
                    <th className="px-4 py-3 text-left font-medium">Cliente</th>
                    <th className="px-4 py-3 text-right font-medium">Total</th>
                    <th className="px-4 py-3 text-center font-medium">Estado</th>
                    <th className="px-4 py-3 text-right font-medium">Fecha</th>
                    <th className="px-4 py-3 text-center font-medium">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-pos-border">
                  {sales.map((s) => (
                    <tr key={s.id} className="hover:bg-pos-surface-hover">
                      <td className="px-4 py-3 font-mono text-xs font-medium">{s.folio}</td>
                      <td className="px-4 py-3">{s.user_name}</td>
                      <td className="px-4 py-3 text-pos-text-secondary">{s.customer_name || '—'}</td>
                      <td className="px-4 py-3 text-right font-semibold">{formatCurrency(s.total)}</td>
                      <td className="px-4 py-3 text-center">
                        <Badge variant={status_variant(s.status)}>
                          {s.status === 'completed' ? 'Completada' : s.status === 'cancelled' ? 'Cancelada' : s.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-pos-text-secondary">{formatDate(s.created_at)}</td>
                      <td className="px-4 py-3 text-center">
                        <Button variant="ghost" size="sm" onClick={() => router.push(`/sales/${s.id}`)}>
                          Ver
                        </Button>
                      </td>
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
          <span>{total} ventas</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</Button>
            <Button variant="outline" size="sm" disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}>Siguiente</Button>
          </div>
        </div>
      )}
    </div>
  )
}
