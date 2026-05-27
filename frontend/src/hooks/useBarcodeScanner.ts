'use client'

import { useEffect, useRef, useCallback } from 'react'

interface UseBarcodeScannerOptions {
  onScan: (barcode: string) => void
  minLength?: number
  timeout?: number
  enabled?: boolean
}

export function useBarcodeScanner({
  onScan,
  minLength = 4,
  timeout = 100,
  enabled = true,
}: UseBarcodeScannerOptions) {
  const buffer = useRef('')
  const lastTime = useRef(0)
  const timer = useRef<ReturnType<typeof setTimeout>>()

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!enabled) return

    const now = Date.now()

    // If the key is Enter, process the buffer as a barcode
    if (e.key === 'Enter') {
      if (timer.current) clearTimeout(timer.current)
      if (buffer.current.length >= minLength) {
        e.preventDefault()
        onScan(buffer.current)
        buffer.current = ''
        return
      }
      buffer.current = ''
      return
    }

    // If it's a printable character, it's likely from a scanner
    if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
      // If too much time passed since last key, start new buffer
      if (now - lastTime.current > timeout * 3) {
        buffer.current = ''
      }

      buffer.current += e.key
      lastTime.current = now

      // Clear previous timer
      if (timer.current) clearTimeout(timer.current)

      // If no more keys within timeout, process as barcode if long enough
      timer.current = setTimeout(() => {
        if (buffer.current.length >= minLength) {
          onScan(buffer.current)
        }
        buffer.current = ''
      }, timeout)

      // Prevent the character from going to focused inputs
      // (only if we detect scanner-like speed)
      if (now - lastTime.current < 50 && buffer.current.length > 1) {
        e.preventDefault()
      }
    }
  }, [onScan, minLength, timeout, enabled])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      if (timer.current) clearTimeout(timer.current)
    }
  }, [handleKeyDown])
}

// Also export a simpler hook for product lookup
export function useBarcodeProductLookup(
  onProductFound: (product: { id: string; name: string; price: number }) => void,
) {
  const { formatCurrency } = require('@/lib/utils')

  const handleScan = useCallback(async (barcode: string) => {
    try {
      const { api } = require('@/lib/api-client')
      const res = await api.get('/api/v1/products/search', { query: barcode, page_size: 1 })
      if (res.items?.[0]) {
        onProductFound(res.items[0])
      }
    } catch {
      // Product not found
    }
  }, [onProductFound])

  return useBarcodeScanner({ onScan: handleScan })
}
