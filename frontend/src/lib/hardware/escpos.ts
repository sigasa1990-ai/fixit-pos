// ESC/POS Command Builder for Thermal Printers
// Compatible with: Epson, Xprinter, Star, Bixolon, Zebra (thermal mode)

export class EscPosBuilder {
  private buffer: number[] = []

  // Initialize printer
  init(): this {
    this.buffer.push(0x1B, 0x40) // ESC @
    return this
  }

  // Line feed
  feed(lines: number = 1): this {
    for (let i = 0; i < lines; i++) {
      this.buffer.push(0x0A) // LF
    }
    return this
  }

  // Feed n lines
  feedN(n: number): this {
    this.buffer.push(0x1B, 0x64, n) // ESC d n
    return this
  }

  // Set character code table (0 = PC437 USA, 2 = PC850, 255 = custom)
  setCharacterTable(table: number = 0): this {
    this.buffer.push(0x1B, 0x74, table) // ESC t n
    return this
  }

  // Text alignment
  alignLeft(): this {
    this.buffer.push(0x1B, 0x61, 0x00) // ESC a 0
    return this
  }
  alignCenter(): this {
    this.buffer.push(0x1B, 0x61, 0x01) // ESC a 1
    return this
  }
  alignRight(): this {
    this.buffer.push(0x1B, 0x61, 0x02) // ESC a 2
    return this
  }

  // Font size
  setFontNormal(): this {
    this.buffer.push(0x1B, 0x21, 0x00) // ESC ! 0
    return this
  }
  setFontBold(): this {
    this.buffer.push(0x1B, 0x45, 0x01) // ESC E 1
    return this
  }
  setFontBoldOff(): this {
    this.buffer.push(0x1B, 0x45, 0x00) // ESC E 0
    return this
  }
  setFontDoubleHeight(): this {
    this.buffer.push(0x1B, 0x21, 0x10) // ESC ! 16 (double height)
    return this
  }
  setFontDoubleWidth(): this {
    this.buffer.push(0x1B, 0x21, 0x20) // ESC ! 32 (double width)
    return this
  }
  setFontDoubleBoth(): this {
    this.buffer.push(0x1B, 0x21, 0x30) // ESC ! 48 (double both)
    return this
  }

  // Underline
  underlineOn(): this {
    this.buffer.push(0x1B, 0x2D, 0x01) // ESC - 1
    return this
  }
  underlineOff(): this {
    this.buffer.push(0x1B, 0x2D, 0x00) // ESC - 0
    return this
  }

  // Text with encoding support
  text(str: string): this {
    const encoded = this.encodeText(str)
    this.buffer.push(...encoded)
    return this
  }

  // Text line with automatic newline
  textLine(str: string): this {
    this.text(str)
    this.buffer.push(0x0A) // LF
    return this
  }

  // Divider line
  divider(char: string = '='): this {
    this.textLine(char.repeat(42))
    return this
  }

  // Separator (lighter)
  separator(): this {
    this.textLine('-'.repeat(42))
    return this
  }

  // Print barcode (Code128)
  barcode128(data: string): this {
    if (data.length === 0) return this
    this.buffer.push(
      0x1D, 0x6B, 0x49, // GS k 73 (Code128)
      data.length,
      ...this.encodeText(data),
      0x00
    )
    return this
  }

  // Print barcode (EAN13)
  barcodeEAN13(data: string): this {
    if (data.length !== 13) data = data.padEnd(13, '0')
    this.buffer.push(
      0x1D, 0x6B, 0x43, // GS k 67 (EAN13)
      12,
      ...this.encodeText(data.substring(0, 12))
    )
    return this
  }

  // Print barcode (UPC-A)
  barcodeUPCA(data: string): this {
    if (data.length !== 12) data = data.padEnd(12, '0')
    this.buffer.push(
      0x1D, 0x6B, 0x43, // GS k 67 (UPC-A)
      11,
      ...this.encodeText(data.substring(0, 11))
    )
    return this
  }

  // Set barcode height
  setBarcodeHeight(height: number = 100): this {
    this.buffer.push(0x1D, 0x68, height) // GS h n
    return this
  }

  // Set barcode width (2-6)
  setBarcodeWidth(width: number = 2): this {
    this.buffer.push(0x1D, 0x77, Math.max(2, Math.min(6, width))) // GS w n
    return this
  }

  // Set barcode text position (0=below, 1=above, 2=none)
  setBarcodeTextPosition(pos: number = 0): this {
    this.buffer.push(0x1D, 0x48, pos) // GS H n
    return this
  }

  // Open cash drawer (ESC/POS standard)
  openDrawer(): this {
    // Standard kick-out connector (pin 2)
    this.buffer.push(0x1B, 0x70, 0x00, 0x19, 0xFA) // ESC p 0 25 250
    return this
  }

  // Open cash drawer with pin 5
  openDrawerPin5(): this {
    this.buffer.push(0x1B, 0x70, 0x01, 0x19, 0xFA) // ESC p 1 25 250
    return this
  }

  // Cut paper (full cut)
  cutFull(): this {
    this.buffer.push(0x1D, 0x56, 0x00) // GS V 0
    return this
  }

  // Cut paper (partial cut)
  cutPartial(): this {
    this.buffer.push(0x1D, 0x56, 0x01) // GS V 1
    return this
  }

  // Beep
  beep(): this {
    this.buffer.push(0x1B, 0x42, 0x03, 0x03) // ESC B 3 3
    return this
  }

  // Build receipt header
  receiptHeader(
    businessName: string,
    rfc?: string,
    address?: string,
    phone?: string,
  ): this {
    this.init()
    this.alignCenter()
    this.setFontDoubleBoth()
    this.textLine(businessName)
    this.setFontNormal()

    if (rfc) this.textLine(`RFC: ${rfc}`)
    if (address) this.textLine(address)
    if (phone) this.textLine(`Tel: ${phone}`)
    this.separator()
    return this
  }

  // Build receipt footer
  receiptFooter(footer?: string, policies?: string): this {
    this.separator()
    this.alignCenter()

    if (footer) {
      this.textLine('')
      footer.split('\n').forEach(line => this.textLine(line.trim()))
    }
    if (policies) {
      this.textLine('')
      policies.split('\n').forEach(line => this.textLine(line.trim()))
    }

    this.textLine('')
    this.textLine('¡Gracias por su compra!')
    this.textLine('')
    this.feedN(4)
    this.cutPartial()
    return this
  }

  // Build sale line item
  saleLine(
    name: string,
    quantity: number,
    price: number,
    total: number,
  ): this {
    this.setFontNormal()
    const line = `${quantity.toFixed(0)}x ${name.substring(0, 22)}`
    this.textLine(line)
    this.alignRight()
    this.textLine(`$${total.toFixed(2)}`)
    this.alignLeft()
    return this
  }

  // Build complete sale receipt
  buildSaleReceipt(
    data: {
      businessName: string
      rfc?: string
      address?: string
      phone?: string
      folio: string
      cashier: string
      date: string
      items: Array<{ name: string; quantity: number; price: number; total: number }>
      subtotal: number
      tax: number
      discount: number
      total: number
      payments: Array<{ method: string; amount: number }>
      footer?: string
      policies?: string
      customer_name?: string
    }
  ): Uint8Array {
    this.receiptHeader(data.businessName, data.rfc, data.address, data.phone)

    this.setFontNormal()
    this.textLine(`Folio: ${data.folio}`)
    this.textLine(`Cajero: ${data.cashier}`)
    this.textLine(`Fecha: ${data.date}`)
    if (data.customer_name) {
      this.textLine(`Cliente: ${data.customer_name}`)
    }
    this.separator()

    // Items
    this.alignLeft()
    this.setFontBold()
    this.textLine('CANT  DESCRIPCION          TOTAL')
    this.setFontBoldOff()

    for (const item of data.items) {
      this.saleLine(item.name, item.quantity, item.price, item.total)
    }
    this.separator()

    // Totals
    this.alignRight()
    this.textLine(`Subtotal: $${data.subtotal.toFixed(2)}`)
    if (data.discount > 0) {
      this.textLine(`Descuento: -$${data.discount.toFixed(2)}`)
    }
    this.textLine(`IVA: $${data.tax.toFixed(2)}`)
    this.setFontDoubleBoth()
    this.textLine(`TOTAL: $${data.total.toFixed(2)}`)
    this.setFontNormal()

    // Payments
    this.separator()
    this.textLine('METODO PAGO         MONTO')
    for (const p of data.payments) {
      const label = this.paymentLabel(p.method)
      this.textLine(`${label.padEnd(18)} $${p.amount.toFixed(2)}`)
    }

    this.receiptFooter(data.footer, data.policies)

    return this.toUint8Array()
  }

  private paymentLabel(method: string): string {
    const labels: Record<string, string> = {
      cash: 'EFECTIVO',
      card: 'TARJETA',
      transfer: 'TRANSFERENCIA',
      usd: 'USD',
      mixed: 'MIXTO',
    }
    return labels[method] || method.toUpperCase()
  }

  // Get buffer as Uint8Array
  toUint8Array(): Uint8Array {
    return new Uint8Array(this.buffer)
  }

  // Get buffer as base64
  toBase64(): string {
    const bytes = this.toUint8Array()
    let binary = ''
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
  }

  // Encode text with Latin-1 (ISO-8859-1) for thermal printer
  private encodeText(str: string): number[] {
    const bytes: number[] = []
    for (let i = 0; i < str.length; i++) {
      const code = str.charCodeAt(i)
      if (code <= 0xFF) {
        bytes.push(code)
      } else {
        // Try to find close approximation or replace
        const approx = this.latin1Approx(code)
        bytes.push(approx)
      }
    }
    return bytes
  }

  private latin1Approx(code: number): number {
    // Common Spanish character mappings
    const map: Record<number, number> = {
      0x2018: 0x27, 0x2019: 0x27, // ' '
      0x201C: 0x22, 0x201D: 0x22, // " "
      0x2013: 0x2D, 0x2014: 0x2D, // - -
      0x00A1: 0x21, // ¡ -> !
      0x00BF: 0x3F, // ¿ -> ?
      0x20AC: 0x45, // € -> E
    }
    return map[code] ?? 0x3F // ? for unknown
  }
}

// Convenience function to create a receipt
export function createSaleReceipt(data: Parameters<EscPosBuilder['buildSaleReceipt']>[0]): Uint8Array {
  return new EscPosBuilder().buildSaleReceipt(data)
}
