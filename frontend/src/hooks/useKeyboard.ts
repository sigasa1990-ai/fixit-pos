'use client'

import { useEffect, useCallback, useRef } from 'react'

export interface Shortcut {
  key: string
  ctrl?: boolean
  alt?: boolean
  shift?: boolean
  description: string
  action: () => void
  enabled?: () => boolean
}

export function useKeyboard(shortcuts: Shortcut[], deps: unknown[] = []) {
  const shortcutsRef = useRef(shortcuts)
  shortcutsRef.current = shortcuts

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in inputs
    const tag = (e.target as HTMLElement).tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
      // Allow Escape and Enter in inputs
      if (e.key !== 'Escape' && e.key !== 'Enter' && e.key !== 'F2' && e.key !== 'F8' && e.key !== 'F11') {
        return
      }
    }

    for (const shortcut of shortcutsRef.current) {
      const matchKey = e.key.toUpperCase() === shortcut.key.toUpperCase()
      const matchCtrl = !!e.ctrlKey === !!shortcut.ctrl
      const matchAlt = !!e.altKey === !!shortcut.alt
      const matchShift = !!e.shiftKey === !!shortcut.shift

      if (matchKey && matchCtrl && matchAlt && matchShift) {
        if (!shortcut.enabled || shortcut.enabled()) {
          e.preventDefault()
          e.stopPropagation()
          shortcut.action()
          return
        }
      }
    }
  }, [])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handleKeyDown, ...deps])
}

// Predefined shortcut sets
export const POS_SHORTCUTS = {
  SEARCH: { key: 'F2', description: 'Buscar producto' },
  PAY: { key: 'F8', description: 'Cobrar / Ir a cobro' },
  CLEAR: { key: 'F11', description: 'Limpiar venta actual' },
  NEW_ORDER: { key: 'N', ctrl: true, description: 'Nueva orden' },
  CANCEL: { key: 'Escape', description: 'Cancelar / Cerrar modal' },
  SHORTCUT_HELP: { key: '/', ctrl: true, description: 'Mostrar atajos' },
  FOCUS_SEARCH: { key: 'F2', description: 'Enfocar búsqueda' },
  PAYMENT_CASH: { key: 'F3', description: 'Seleccionar efectivo' },
  PAYMENT_CARD: { key: 'F4', description: 'Seleccionar tarjeta' },
  PRINT_LAST: { key: 'F9', description: 'Reimprimir último ticket' },
}
