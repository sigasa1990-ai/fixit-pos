import type { Metadata } from 'next'
import { AppLayout } from '@/components/layout/AppLayout'
import './globals.css'

export const metadata: Metadata = {
  title: 'FIXIT POS',
  description: 'Sistema de Punto de Venta',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es">
      <body>
        <AppLayout>{children}</AppLayout>
      </body>
    </html>
  )
}
