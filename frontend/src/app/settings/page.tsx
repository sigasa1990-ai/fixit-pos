'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { usePrinter } from '@/hooks/usePrinter'
import { createProductLabel, createPriceLabel, createBinLabel } from '@/lib/hardware/labels'
import { EscPosBuilder } from '@/lib/hardware/escpos'
import { QrCode, Printer, Wifi, WifiOff, RefreshCw, TestTube, DollarSign } from 'lucide-react'
import toast from 'react-hot-toast'
import { Toaster } from 'react-hot-toast'

export default function SettingsPage() {
  const router = useRouter()
  const { is_authenticated, permissions } = useAuthStore()
  const printer = usePrinter()
  const [test_barcode, setTestBarcode] = useState('7501001234567')
  const [test_product, setTestProduct] = useState('PRODUCTO DE PRUEBA')
  const [test_price, setTestPrice] = useState('99.99')
  const [connecting, setConnecting] = useState(false)

  useEffect(() => {
    if (!is_authenticated) {
      const token = localStorage.getItem('fixit_token')
      if (!token) router.push('/login')
    }
  }, [is_authenticated, router])

  const handleConnect = async () => {
    setConnecting(true)
    try {
      await printer.connect()
      toast.success('Conectado a QZ Tray')
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : 'No se pudo conectar'}`)
    } finally {
      setConnecting(false)
    }
  }

  const handleTestPrint = async () => {
    if (!printer.selectedPrinter) {
      toast.error('Seleccione una impresora primero')
      return
    }
    try {
      const escpos = new EscPosBuilder()
      escpos.init()
        .alignCenter()
        .setFontDoubleBoth()
        .textLine('FIXIT POS')
        .setFontNormal()
        .textLine('Impresión de prueba')
        .separator()
        .textLine('Si ve esto, la impresora')
        .textLine('funciona correctamente.')
        .textLine('')
        .setFontBold()
        .textLine('FECHA: ' + new Date().toLocaleString('es-MX'))
        .setFontBoldOff()
        .separator()
        .textLine('¡Gracias!')
        .feedN(3)
        .cutPartial()

      const base64 = escpos.toBase64()
      await printer.connect()
      // Actualizar la conexión primero si es necesario
      setTimeout(async () => {
        try {
          const { qzTray } = await import('@/lib/hardware/qztray')
          await qzTray.print(base64, printer.selectedPrinter!)
          toast.success('Impresión de prueba enviada')
        } catch (err) {
          toast.error(`Error: ${err instanceof Error ? err.message : ''}`)
        }
      }, 500)
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : ''}`)
    }
  }

  const handleOpenDrawer = async () => {
    try {
      await printer.openDrawer()
      toast.success('Cajón abierto')
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : ''}`)
    }
  }

  const handleTestLabel = async () => {
    if (!printer.selectedPrinter) {
      toast.error('Seleccione una impresora primero')
      return
    }
    try {
      const zpl = createProductLabel({
        name: test_product,
        price: parseFloat(test_price) || 0,
        barcode: test_barcode,
        product_code: 'PRD-000001',
      })
      const base64 = btoa(zpl)
      const { qzTray } = await import('@/lib/hardware/qztray')
      await qzTray.print(base64, printer.selectedPrinter)
      toast.success('Etiqueta enviada a imprimir')
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : ''}`)
    }
  }

  const handleTestPriceLabel = async () => {
    if (!printer.selectedPrinter) {
      toast.error('Seleccione una impresora primero')
      return
    }
    try {
      const zpl = createPriceLabel({
        name: test_product,
        price: parseFloat(test_price) || 0,
        barcode: test_barcode,
      })
      const base64 = btoa(zpl)
      const { qzTray } = await import('@/lib/hardware/qztray')
      await qzTray.print(base64, printer.selectedPrinter)
      toast.success('Etiqueta de precio enviada')
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : ''}`)
    }
  }

  if (!is_authenticated) return null

  return (
    <div className="p-6">
      <Toaster position="top-right" />
      <h1 className="mb-6 text-2xl font-bold text-pos-text">Configuración de Hardware</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* QZ Tray Connection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Printer className="h-5 w-5" />
              QZ Tray
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-pos-border p-3">
              <div className="flex items-center gap-2">
                {printer.connected ? (
                  <Wifi className="h-5 w-5 text-pos-success" />
                ) : (
                  <WifiOff className="h-5 w-5 text-pos-text-secondary" />
                )}
                <div>
                  <div className="text-sm font-medium">
                    {printer.connected ? 'Conectado' : 'Desconectado'}
                  </div>
                  <div className="text-xs text-pos-text-secondary">
                    {printer.connected
                      ? `Impresora: ${printer.selectedPrinter || 'Ninguna'}`
                      : 'QZ Tray no detectado'}
                  </div>
                </div>
              </div>
              <Button
                onClick={handleConnect}
                disabled={connecting || printer.connected}
                size="sm"
              >
                {connecting ? 'Conectando...' : 'Conectar'}
              </Button>
            </div>

            {/* Printer selection */}
            {printer.connected && (
              <div>
                <label className="mb-1 text-sm font-medium text-pos-text">
                  Impresora predeterminada
                </label>
                <select
                  value={printer.selectedPrinter || ''}
                  onChange={(e) => printer.setPrinter(e.target.value)}
                  className="w-full rounded-md border border-pos-border px-3 py-2 text-sm"
                >
                  <option value="">Seleccionar impresora</option>
                  {printer.printers.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Printing Tests */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TestTube className="h-5 w-5" />
              Pruebas de Impresión
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button onClick={handleTestPrint} className="w-full" disabled={!printer.connected}>
              Imprimir Ticket de Prueba
            </Button>
            <Button onClick={handleOpenDrawer} className="w-full" variant="secondary" disabled={!printer.connected}>
              Abrir Cajón de Dinero
            </Button>

            <hr className="border-pos-border" />

            <div className="text-sm font-medium text-pos-text">Impresión de Etiquetas</div>
            <input
              placeholder="Código de barras"
              value={test_barcode}
              onChange={(e) => setTestBarcode(e.target.value)}
              className="w-full rounded-md border border-pos-border px-3 py-2 text-sm"
            />
            <input
              placeholder="Nombre del producto"
              value={test_product}
              onChange={(e) => setTestProduct(e.target.value)}
              className="w-full rounded-md border border-pos-border px-3 py-2 text-sm"
            />
            <input
              type="number"
              placeholder="Precio"
              value={test_price}
              onChange={(e) => setTestPrice(e.target.value)}
              className="w-full rounded-md border border-pos-border px-3 py-2 text-sm"
            />

            <div className="flex gap-2">
              <Button onClick={handleTestLabel} className="flex-1" disabled={!printer.connected}>
                <QrCode className="mr-1 h-4 w-4" />
                Etiqueta Prod.
              </Button>
              <Button onClick={handleTestPriceLabel} className="flex-1" variant="secondary" disabled={!printer.connected}>
                <DollarSign className="mr-1 h-4 w-4" />
                Etiqueta Precio
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* ESC/POS Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5" />
              Configuración de Impresión
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="rounded-lg bg-blue-50 p-3 text-blue-700">
              <strong>Impresión automática:</strong> Al completar una venta, el ticket se imprime
              automáticamente si QZ Tray está conectado.
            </div>
            <div className="rounded-lg bg-blue-50 p-3 text-blue-700">
              <strong>Cajón de dinero:</strong> Se abre automáticamente al cobrar en efectivo.
            </div>
            <div className="rounded-lg bg-amber-50 p-3 text-amber-700">
              <strong>Formato de ticket:</strong> ESC/POS (térmico) con soporte para códigos de barras.
            </div>
            <div className="rounded-lg bg-green-50 p-3 text-green-700">
              <strong>Compatibilidad:</strong> Epson, Xprinter, Star, Bixolon, Zebra (térmico).
            </div>
          </CardContent>
        </Card>

        {/* Scanner Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <QrCode className="h-5 w-5" />
              Escáner de Código de Barras
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p className="text-pos-text-secondary">
              El escáner de código de barras funciona automáticamente como emulación de teclado (USB HID).
              No requiere configuración adicional.
            </p>
            <div className="rounded-lg bg-green-50 p-3 text-green-700">
              <strong>Plug & Play:</strong> Conecte el escáner vía USB. El sistema detecta la entrada
              del escáner automáticamente y busca el producto.
            </div>
            <div className="rounded-lg bg-gray-50 p-3 text-gray-600">
              <strong>Formatos soportados:</strong> Code128, EAN-13, UPC-A, EAN-8, Código de barras
              de 8-14 dígitos.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
