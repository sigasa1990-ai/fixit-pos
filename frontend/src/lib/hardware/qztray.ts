// QZ Tray Connection Manager
// QZ Tray is a local WebSocket server for POS peripheral communication
// Docs: https://qz.io/wiki/

const QZ_TRAY_WS = 'ws://localhost:8181'
const QZ_TRAY_HTTPS = 'wss://localhost:8182'

type QzTrayStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

export interface QzTrayState {
  status: QzTrayStatus
  printer: string | null
  printers: string[]
  error: string | null
}

type StatusListener = (status: QzTrayState) => void

// In-memory promise-based queue for QZ Tray operations
class QzTrayManager {
  private ws: WebSocket | null = null
  private requestId = 0
  private pending = new Map<number, { resolve: (v: unknown) => void; reject: (e: Error) => void }>()
  private _status: QzTrayStatus = 'disconnected'
  private _printer: string | null = null
  private _printers: string[] = []
  private listeners: StatusListener[] = []
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private connected = false

  get status() { return this._status }
  get printer() { return this._printer }
  get printers() { return this._printers }

  setPrinter(name: string) {
    this._printer = name
    if (typeof window !== 'undefined') {
      localStorage.setItem('fixit_printer', name)
    }
    this.notify()
  }

  loadSavedPrinter(): string | null {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('fixit_printer')
      if (saved) this._printer = saved
      return saved
    }
    return null
  }

  subscribe(listener: StatusListener): () => void {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener)
    }
  }

  private notify() {
    const state = this.getState()
    this.listeners.forEach(l => l(state))
  }

  private getState(): QzTrayState {
    return {
      status: this._status,
      printer: this._printer,
      printers: this._printers,
      error: null,
    }
  }

  async connect(): Promise<void> {
    if (this.connected) return

    this._status = 'connecting'
    this.notify()

    try {
      const url = QZ_TRAY_WS
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        this._status = 'connected'
        this.connected = true
        this.notify()
        this.discoverPrinters()
      }

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          this.handleMessage(msg)
        } catch {
          // Ignore non-JSON messages
        }
      }

      this.ws.onerror = () => {
        this._status = 'error'
        this.connected = false
        this.notify()
        this.scheduleReconnect()
      }

      this.ws.onclose = () => {
        this._status = 'disconnected'
        this.connected = false
        this.notify()
        this.scheduleReconnect()
      }
    } catch (err) {
      this._status = 'error'
      this.connected = false
      this.notify()
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, 5000)
  }

  private handleMessage(msg: { id?: number; result?: unknown; error?: string; event?: string }) {
    if (msg.id !== undefined && this.pending.has(msg.id)) {
      const pending = this.pending.get(msg.id)!
      this.pending.delete(msg.id)
      if (msg.error) {
        pending.reject(new Error(msg.error))
      } else {
        pending.resolve(msg.result)
      }
    }
  }

  private async send(method: string, params: unknown[] = []): Promise<unknown> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('QZ Tray no está conectado')
    }

    const id = ++this.requestId
    const payload = JSON.stringify({ id, method, params })

    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws!.send(payload)

      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id)
          reject(new Error('Timeout: QZ Tray no respondió'))
        }
      }, 30000)
    })
  }

  // === PRINTING ===

  async discoverPrinters(): Promise<string[]> {
    try {
      const result = await this.send('findPrinters')
      const printers = (result as string[]) || []
      this._printers = printers
      this.notify()

      // Auto-select saved printer
      const saved = this.loadSavedPrinter()
      if (saved && printers.includes(saved)) {
        this._printer = saved
      } else if (printers.length > 0 && !this._printer) {
        this._printer = printers[0]
      }
      return printers
    } catch {
      this._printers = []
      return []
    }
  }

  async print(base64Data: string, printerName?: string): Promise<void> {
    const printer = printerName || this._printer
    if (!printer) throw new Error('No hay impresora seleccionada')

    await this.send('print', [
      printer,
      base64Data,
      {
        type: 'raw',    // RAW ESC/POS data
        encoding: 'base64',
        copies: 1,
      },
    ])
  }

  async printImage(imageBase64: string, printerName?: string): Promise<void> {
    const printer = printerName || this._printer
    if (!printer) throw new Error('No hay impresora seleccionada')

    await this.send('print', [
      printer,
      imageBase64,
      {
        type: 'image',
        format: 'base64',
        copies: 1,
      },
    ])
  }

  async printHTML(html: string, printerName?: string): Promise<void> {
    const printer = printerName || this._printer
    if (!printer) throw new Error('No hay impresora seleccionada')

    await this.send('print', [
      printer,
      html,
      {
        type: 'html',
        copies: 1,
      },
    ])
  }

  async openCashDrawer(printerName?: string): Promise<void> {
    const printer = printerName || this._printer
    if (!printer) throw new Error('No hay impresora seleccionada')

    // Send ESC/POS cash drawer command
    const drawerCommand = new Uint8Array([0x1B, 0x70, 0x00, 0x19, 0xFA])
    const base64 = btoa(Array.from(drawerCommand, (byte) => String.fromCharCode(byte)).join(''))

    await this.send('print', [
      printer,
      base64,
      {
        type: 'raw',
        encoding: 'base64',
        copies: 1,
      },
    ])
  }

  // === STATUS ===

  async getPrinters(): Promise<string[]> {
    const result = await this.send('findPrinters')
    const printers = (result as string[]) || []
    this._printers = printers
    this.notify()
    return printers
  }

  async getPrinterStatus(printerName?: string): Promise<string> {
    const printer = printerName || this._printer
    if (!printer) return 'No printer selected'
    try {
      const result = await this.send('printerStatus', [printer])
      return result as string
    } catch {
      return 'Unknown'
    }
  }

  // Disconnect
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connected = false
    this._status = 'disconnected'
    this.notify()
  }
}

export const qzTray = new QzTrayManager()
