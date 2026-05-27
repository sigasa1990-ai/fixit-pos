'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Search, Barcode } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { Product } from '@/types'

interface ProductSearchProps {
  onProductSelect: (product: Product) => void
  autoFocus?: boolean
}

export function ProductSearch({ onProductSelect, autoFocus = true }: ProductSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Product[]>([])
  const [is_open, setIsOpen] = useState(false)
  const [selected_idx, setSelectedIdx] = useState(0)
  const [loading, setLoading] = useState(false)
  const input_ref = useRef<HTMLInputElement>(null)
  const debounce_ref = useRef<ReturnType<typeof setTimeout>>()

  const search = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([])
      setIsOpen(false)
      return
    }
    setLoading(true)
    try {
      const res = await api.get<{ items: Product[]; total: number }>('/api/v1/products/search', {
        query: q,
        page_size: 10,
        is_active: true,
      })
      setResults(res.items || [])
      setIsOpen(res.items?.length > 0)
      setSelectedIdx(0)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (debounce_ref.current) clearTimeout(debounce_ref.current)
    debounce_ref.current = setTimeout(() => search(query), 200)
    return () => { if (debounce_ref.current) clearTimeout(debounce_ref.current) }
  }, [query, search])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIdx(prev => Math.min(prev + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIdx(prev => Math.max(prev - 1, 0))
    } else if (e.key === 'Enter' && results[selected_idx]) {
      e.preventDefault()
      onProductSelect(results[selected_idx])
      setQuery('')
      input_ref.current?.focus()
    } else if (e.key === 'Escape') {
      setIsOpen(false)
      input_ref.current?.blur()
    }
  }

  // Detectar entrada de escáner (ráfaga rápida de caracteres)
  const scan_buffer = useRef('')
  const scan_timeout = useRef<ReturnType<typeof setTimeout>>()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    scan_buffer.current = val

    if (scan_timeout.current) clearTimeout(scan_timeout.current)
    scan_timeout.current = setTimeout(() => {
      // Si el valor es un código de barras (solo dígitos, longitud típica)
      if (/^\d{8,}$/.test(val)) {
        search(val)
      }
    }, 300)

    setQuery(val)
  }

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pos-text-secondary" />
        <Input
          ref={input_ref}
          type="text"
          placeholder="Buscar por nombre, código o barras... (F2)"
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          className="h-12 pl-10 text-base"
          autoFocus={autoFocus}
        />
        <Barcode className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pos-text-secondary" />
      </div>

      {is_open && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-pos-border bg-white shadow-lg">
          {loading && (
            <div className="p-3 text-center text-sm text-pos-text-secondary">
              Buscando...
            </div>
          )}
          {results.map((product, idx) => (
            <button
              key={product.id}
              className={`flex w-full items-center gap-3 px-4 py-3 text-left text-sm transition-colors
                ${idx === selected_idx ? 'bg-pos-primary/10' : 'hover:bg-pos-surface-hover'}
                ${idx === 0 ? 'rounded-t-lg' : ''}
                ${idx === results.length - 1 ? 'rounded-b-lg' : ''}`}
              onMouseDown={() => {
                onProductSelect(product)
                setQuery('')
              }}
            >
              <div className="flex-1">
                <div className="font-medium text-pos-text">{product.name}</div>
                <div className="text-xs text-pos-text-secondary">
                  {product.product_code}
                  {product.barcode && ` · ${product.barcode}`}
                </div>
              </div>
              <div className="text-right">
                <div className="font-semibold text-pos-primary">
                  ${product.price.toFixed(2)}
                </div>
                {product.track_inventory && (
                  <div className="text-xs text-pos-text-secondary">Costo: ${product.cost.toFixed(2)}</div>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
