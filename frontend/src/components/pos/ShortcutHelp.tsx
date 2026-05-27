'use client'

import { Dialog, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { POS_SHORTCUTS } from '@/hooks/useKeyboard'

interface ShortcutHelpProps {
  open: boolean
  onClose: () => void
}

const shortcuts = [
  { keys: ['F2'], desc: 'Buscar producto / Enfocar búsqueda' },
  { keys: ['F8'], desc: 'Cobrar venta actual' },
  { keys: ['F11'], desc: 'Limpiar venta actual' },
  { keys: ['Ctrl', 'N'], desc: 'Nueva orden' },
  { keys: ['Esc'], desc: 'Cancelar / Cerrar modal' },
  { keys: ['Ctrl', '/'], desc: 'Mostrar esta ayuda' },
  { keys: ['+'], desc: 'Nueva orden (botón)' },
  { keys: ['↑', '↓'], desc: 'Navegar resultados de búsqueda' },
  { keys: ['Enter'], desc: 'Seleccionar producto / Confirmar' },
  { separator: true },
  { keys: ['F3'], desc: 'Pago en efectivo' },
  { keys: ['F4'], desc: 'Pago con tarjeta' },
  { keys: ['F9'], desc: 'Reimprimir último ticket' },
  { keys: ['F12'], desc: 'Abrir configuración' },
]

export function ShortcutHelp({ open, onClose }: ShortcutHelpProps) {
  const renderKeys = (keys: string[]) => (
    <div className="flex items-center gap-1">
      {keys.map((key, i) => (
        <span key={i}>
          <kbd className="inline-flex min-w-[28px] items-center justify-center rounded-md border border-pos-border bg-pos-surface-hover px-2 py-0.5 font-mono text-xs font-medium shadow-sm">
            {key}
          </kbd>
          {i < keys.length - 1 && <span className="mx-0.5 text-pos-text-secondary">+</span>}
        </span>
      ))}
    </div>
  )

  return (
    <Dialog open={open} onClose={onClose}>
      <DialogHeader>
        <DialogTitle>Atajos de Teclado</DialogTitle>
      </DialogHeader>

      <div className="max-h-80 overflow-y-auto">
        <div className="space-y-1">
          {shortcuts.map((s, i) => {
            if ('separator' in s) {
              return <hr key={i} className="my-2 border-pos-border" />
            }
            return (
              <div key={i} className="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-pos-surface-hover">
                <span className="text-sm text-pos-text">{s.desc}</span>
                {'keys' in s && renderKeys(s.keys as string[])}
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-4 rounded-md bg-pos-surface-hover p-2 text-center text-xs text-pos-text-secondary">
        Los atajos funcionan en toda la pantalla POS
      </div>
    </Dialog>
  )
}
