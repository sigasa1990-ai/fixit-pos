'use client'

import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api-client'
import { formatCurrency, formatDate } from '@/lib/utils'
import { Plus, Search, Package } from 'lucide-react'
import type { Product, PaginatedResponse } from '@/types'

export default function ProductsPage() {
  const router = useRouter()
  const { is_authenticated, permissions } = useAuthStore()
  const [products, setProducts] = useState<Product[]>([])
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [show_form, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', price: '', cost: '', barcode: '' })

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
      const res = await api.get<PaginatedResponse<Product>>('/api/v1/products/search', { query, page, page_size: 20 })
      setProducts(res.items || [])
      setTotal(res.total || 0)
    } catch {
      setProducts([])
    } finally {
      setLoading(false)
    }
  }

  const createProduct = async () => {
    if (!form.name || !form.price) return
    try {
      await api.post('/api/v1/products', {
        name: form.name,
        price: parseFloat(form.price),
        cost: parseFloat(form.cost) || 0,
        barcode: form.barcode || undefined,
      })
      setForm({ name: '', price: '', cost: '', barcode: '' })
      setShowForm(false)
      search()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Error al crear producto')
    }
  }

  if (!is_authenticated) return null
  const can_create = permissions.includes('product.create')

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-pos-text">Productos</h1>
        {can_create && (
          <Button onClick={() => setShowForm(!show_form)}>
            <Plus className="mr-1 h-4 w-4" />
            Nuevo
          </Button>
        )}
      </div>

      <div className="mb-4 flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pos-text-secondary" />
          <Input
            placeholder="Buscar por nombre, código o barras..."
            value={query}
            onChange={(e) => { setQuery(e.target.value); setPage(1) }}
            className="pl-10"
          />
        </div>
      </div>

      {show_form && (
        <Card className="mb-6">
          <CardHeader><CardTitle>Nuevo Producto</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <Input placeholder="Nombre *" value={form.name} onChange={(e) => setForm(p => ({ ...p, name: e.target.value }))} />
              <Input type="number" placeholder="Precio *" value={form.price} onChange={(e) => setForm(p => ({ ...p, price: e.target.value }))} />
              <Input type="number" placeholder="Costo" value={form.cost} onChange={(e) => setForm(p => ({ ...p, cost: e.target.value }))} />
              <Input placeholder="Código barras" value={form.barcode} onChange={(e) => setForm(p => ({ ...p, barcode: e.target.value }))} />
            </div>
            <Button className="mt-3" onClick={createProduct}>Guardar</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-pos-text-secondary">Cargando...</div>
          ) : products.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-8 text-pos-text-secondary">
              <Package className="h-8 w-8" />
              <span>No se encontraron productos</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-pos-border bg-pos-surface-hover">
                    <th className="px-4 py-3 text-left font-medium">Código</th>
                    <th className="px-4 py-3 text-left font-medium">Nombre</th>
                    <th className="px-4 py-3 text-left font-medium">Barras</th>
                    <th className="px-4 py-3 text-right font-medium">Precio</th>
                    <th className="px-4 py-3 text-right font-medium">Costo</th>
                    <th className="px-4 py-3 text-center font-medium">Estado</th>
                    <th className="px-4 py-3 text-right font-medium">Creado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-pos-border">
                  {products.map((p) => (
                    <tr key={p.id} className="hover:bg-pos-surface-hover">
                      <td className="px-4 py-3 font-mono text-xs">{p.product_code}</td>
                      <td className="px-4 py-3 font-medium">{p.name}</td>
                      <td className="px-4 py-3 font-mono text-xs text-pos-text-secondary">{p.barcode || '—'}</td>
                      <td className="px-4 py-3 text-right font-semibold">{formatCurrency(p.price)}</td>
                      <td className="px-4 py-3 text-right text-pos-text-secondary">{formatCurrency(p.cost)}</td>
                      <td className="px-4 py-3 text-center">
                        <Badge variant={p.is_active ? 'success' : 'secondary'}>
                          {p.is_active ? 'Activo' : 'Inactivo'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right text-xs text-pos-text-secondary">{formatDate(p.created_at)}</td>
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
          <span>{total} productos</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Anterior</Button>
            <Button variant="outline" size="sm" disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}>Siguiente</Button>
          </div>
        </div>
      )}
    </div>
  )
}
