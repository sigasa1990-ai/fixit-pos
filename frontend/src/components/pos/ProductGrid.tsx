'use client'

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/lib/api-client'
import { formatCurrency } from '@/lib/utils'
import { Package } from 'lucide-react'
import type { Product } from '@/types'

interface ProductGridProps {
  onProductSelect: (product: Product) => void
  location_id: string
}

export function ProductGrid({ onProductSelect, location_id }: ProductGridProps) {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)

  // Load initial batch
  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async (searchPage = 1) => {
    setLoading(true)
    try {
      const res = await api.get<{ items: Product[]; total: number }>('/api/v1/products/search', {
        page: searchPage,
        page_size: 50,
        is_active: true,
      })
      if (searchPage === 1) {
        setProducts(res.items || [])
      } else {
        setProducts(prev => [...prev, ...(res.items || [])])
      }
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  const loadMore = () => {
    const next = page + 1
    setPage(next)
    loadProducts(next + 1)
  }

  return (
    <div>
      {loading && products.length === 0 ? (
        <div className="flex items-center justify-center py-12 text-sm text-pos-text-secondary">
          Cargando productos...
        </div>
      ) : products.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-sm text-pos-text-secondary">
          <Package className="mb-2 h-8 w-8" />
          No hay productos disponibles
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5">
            {products.map((product) => (
              <button
                key={product.id}
                onClick={() => onProductSelect(product)}
                className="group flex flex-col items-center justify-center rounded-lg border border-pos-border bg-white p-3 text-center transition-all hover:border-pos-primary hover:shadow-md active:scale-95"
              >
                <div className="mb-1 flex h-10 w-10 items-center justify-center rounded-full bg-pos-primary/10 text-pos-primary">
                  <Package className="h-5 w-5" />
                </div>
                <div className="w-full truncate text-xs font-medium text-pos-text" title={product.name}>
                  {product.name}
                </div>
                <div className="mt-0.5 text-sm font-bold text-pos-primary">
                  {formatCurrency(product.price)}
                </div>
                <div className="text-[10px] text-pos-text-secondary">
                  {product.product_code}
                </div>
              </button>
            ))}
          </div>

          {products.length >= 50 && (
            <button
              onClick={loadMore}
              className="mt-4 w-full rounded-lg border border-dashed border-pos-border py-3 text-sm text-pos-text-secondary transition-colors hover:border-pos-primary hover:text-pos-primary"
            >
              Cargar más productos
            </button>
          )}
        </>
      )}
    </div>
  )
}
