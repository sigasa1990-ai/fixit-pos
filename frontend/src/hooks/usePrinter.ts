'use client'

import { useState, useEffect, useCallback } from 'react'
import { qzTray } from '@/lib/hardware/qztray'
import { createSaleReceipt, EscPosBuilder } from '@/lib/hardware/escpos'
import { buildHtmlReceipt, type TicketData } from '@/lib/hardware/templates'
import type { QzTrayState } from '@/lib/hardware/qztray'

interface UsePrinterReturn {
  connected: boolean
  connecting: boolean
  status: string
  printers: string[]
  selectedPrinter: string | null
  error: string | null
  connect: () => Promise<void>
  setPrinter: (name: string) => void
  printReceipt: (data: TicketData) => Promise<void>
  printHtmlReceipt: (data: TicketData) => Promise<void>
  openDrawer: () => Promise<void>
  printLabel: (zpl: string) => Promise<void>
}

export function usePrinter(): UsePrinterReturn {
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [status, setStatus] = useState('disconnected')
  const [printers, setPrinters] = useState<string[]>([])
  const [selectedPrinter, setSelectedPrinter] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const saved = qzTray.loadSavedPrinter()
    if (saved) setSelectedPrinter(saved)

    const unsub = qzTray.subscribe((state) => {
      setConnected(state.status === 'connected')
      setStatus(state.status)
      setPrinters(state.printers)
      setSelectedPrinter(state.printer)
    })

    return unsub
  }, [])

  const connect = useCallback(async () => {
    setConnecting(true)
    setError(null)
    try {
      await qzTray.connect()
      setConnected(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de conexión')
    } finally {
      setConnecting(false)
    }
  }, [])

  const handleSetPrinter = useCallback((name: string) => {
    qzTray.setPrinter(name)
    setSelectedPrinter(name)
  }, [])

  const printReceipt = useCallback(async (data: TicketData) => {
    try {
      const escpos = new EscPosBuilder()
      const receipt = escpos.buildSaleReceipt({
        businessName: data.businessName,
        rfc: data.rfc,
        address: data.address,
        phone: data.phone,
        folio: data.folio,
        cashier: data.cashier,
        date: data.date,
        items: data.items,
        subtotal: data.subtotal,
        tax: data.tax,
        discount: data.discount,
        total: data.total,
        payments: data.payments,
        footer: data.footer,
        policies: data.policies,
        customer_name: data.customer_name,
      })

      const base64 = btoa(Array.from(receipt, (byte) => String.fromCharCode(byte)).join(''))
      await qzTray.print(base64, selectedPrinter || undefined)
    } catch (err) {
      throw new Error(`Error de impresión: ${err instanceof Error ? err.message : 'desconocido'}`)
    }
  }, [selectedPrinter])

  const printHtmlReceipt = useCallback(async (data: TicketData) => {
    try {
      const html = buildHtmlReceipt(data)
      await qzTray.printHTML(html, selectedPrinter || undefined)
    } catch (err) {
      throw new Error(`Error de impresión HTML: ${err instanceof Error ? err.message : 'desconocido'}`)
    }
  }, [selectedPrinter])

  const openDrawer = useCallback(async () => {
    try {
      await qzTray.openCashDrawer(selectedPrinter || undefined)
    } catch (err) {
      throw new Error(`Error al abrir cajón: ${err instanceof Error ? err.message : 'desconocido'}`)
    }
  }, [selectedPrinter])

  const printLabel = useCallback(async (zpl: string) => {
    try {
      const base64 = btoa(zpl)
      await qzTray.print(base64, selectedPrinter || undefined)
    } catch (err) {
      throw new Error(`Error al imprimir etiqueta: ${err instanceof Error ? err.message : 'desconocido'}`)
    }
  }, [selectedPrinter])

  return {
    connected,
    connecting,
    status,
    printers,
    selectedPrinter,
    error,
    connect,
    setPrinter: handleSetPrinter,
    printReceipt,
    printHtmlReceipt,
    openDrawer,
    printLabel,
  }
}
