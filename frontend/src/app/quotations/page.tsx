'use client'

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { useRouter } from 'next/navigation'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api-client'
import { formatCurrency, formatDate } from '@/lib/utils'
import { FileText } from 'lucide-react'
import type { Quotation, PaginatedResponse } from '@/types'

export default function QuotationsPage() {
  const router = useRouter()
  const { is_authenticated } = useAuthStore()
  const [quotations, setQuotations] = useState<Quotation[]>([])
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
      const res = await api.get<PaginatedResponse<Quotation>>('/api/v1/quotations/search', { page, page_size: 20 })
      setQuotations(res.items || [])
      setTotal(res.total || 0)
    } catch {
      setQuotations([])
    } finally {
      setLoading(false)
    }
  }

  const status_variant = (status: string) => {
    if (status === 'active') return 'success' as const
    if (status === 'converted') return 'secondary' as const
    if (status === 'cancelled') return 'danger' as const
    return 'warning' as const
  }

  const status_label = (status: string) => {
    const labels: Record<string, string> = {
      draft: 'Borrador',
      active: 'Activa',
      converted: 'Convertida',
      cancelled: 'Cancelada',
      parked: 'Pausada',
    }
    return labels[status] || status
  }

  if (!is_authenticated) return null

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-pos-text">Cotizaciones</h1>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-pos-text-secondary">Cargando...</div>
          ) : quotations.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-8 text-pos-text-secondary">
              <FileText className="h-8 w-8" />
              <span>No se encontraron cotizaciones</span>
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
                    <th className="px-4 py-3 text-right font-medium">Válido hasta</th>
                    <th className="px-4 py-3 text-right font-medium">Creado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-pos-border">
                  {quotations.map((q) => (
                    <tr key={q.id} className="hover:bg-pos-surface-hover">
                      <td className="px-4 py-3 font-mono text-xs font-medium">{q.folio}</td>
                      <td className="px-4 py-3">{q.user_name}</td>
                      <td className="px-4 py-3 text-pos-text-secondary">{q.customer_name || '—'}</td>
                      <td className="px-4 py-3 text-right font-semibold">{formatCurrency(q.total)}</td>
                      <td className="px-4 py-3 text-center">
                        <Badge variant={status_variant(q.status)}>{status_label(q.status)}</Badge>
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-pos-text-secondary">
                        {q.valid_until ? formatDate(q.valid_until) : '—'}
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-pos-text-secondary">{formatDate(q.created_at)}</td>
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
          <span>{total} cotizaciones</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</Button>
            <Button variant="outline" size="sm" disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}>Siguiente</Button>
          </div>
        </div>
      )}
    </div>
  )
}
