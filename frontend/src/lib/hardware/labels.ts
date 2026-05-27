// Barcode label generators
// Compatible with: Zebra, TSC, Brother, Xprinter label printers

// ZPL (Zebra Programming Language) label builder
export class ZplBuilder {
  private commands: string[] = []
  private dpi: number = 203

  constructor(labelWidthMm: number = 50, labelHeightMm: number = 30, dpi: number = 203) {
    this.dpi = dpi
    const widthDots = Math.round(labelWidthMm * dpi / 25.4)
    const heightDots = Math.round(labelHeightMm * dpi / 25.4)
    this.commands.push(`^XA`)                    // Start label
    this.commands.push(`^LL${heightDots}`)       // Label length
    this.commands.push(`^PW${widthDots}`)        // Label width
    this.commands.push(`^LS0`)                   // No shift
    this.commands.push(`^CF0,20`)                // Default font
  }

  // Set font
  font(name: string = '0', size: number = 20): this {
    this.commands.push(`^CF${name},${size}`)
    return this
  }

  // Set position
  at(x: number, y: number): this {
    const xDots = Math.round(x * this.dpi / 25.4)
    const yDots = Math.round(y * this.dpi / 25.4)
    this.commands.push(`^FO${xDots},${yDots}`)
    return this
  }

  // Text
  text(content: string): this {
    this.commands.push(`^FD${content}^FS`)
    return this
  }

  // Barcode Code128
  barcode128(data: string, heightMm: number = 15): this {
    const heightDots = Math.round(heightMm * this.dpi / 25.4)
    this.commands.push(`^BY2,3,${heightDots}`)   // Barcode settings
    this.commands.push(`^BCN,${heightDots},Y,N,N`) // Code128
    this.commands.push(`^FD${data}^FS`)
    return this
  }

  // Barcode EAN13
  barcodeEAN13(data: string, heightMm: number = 15): this {
    const heightDots = Math.round(heightMm * this.dpi / 25.4)
    this.commands.push(`^BY2,3,${heightDots}`)
    this.commands.push(`^BEN,${heightDots},Y,N`)  // EAN13
    this.commands.push(`^FD${data}^FS`)
    return this
  }

  // Barcode UPC-A
  barcodeUPCA(data: string, heightMm: number = 15): this {
    const heightDots = Math.round(heightMm * this.dpi / 25.4)
    this.commands.push(`^BY2,3,${heightDots}`)
    this.commands.push(`^BUN,${heightDots},Y,N`)  // UPC-A
    this.commands.push(`^FD${data}^FS`)
    return this
  }

  // QR Code
  qrCode(data: string, sizeMm: number = 20): this {
    const sizeDots = Math.round(sizeMm * this.dpi / 25.4)
    this.commands.push(`^BQN,2,${sizeDots}`)
    this.commands.push(`^FDHM,${data}^FS`)
    return this
  }

  // Draw rectangle (for borders or boxes)
  rectangle(x: number, y: number, widthMm: number, heightMm: number): this {
    const xDots = Math.round(x * this.dpi / 25.4)
    const yDots = Math.round(y * this.dpi / 25.4)
    const wDots = Math.round(widthMm * this.dpi / 25.4)
    const hDots = Math.round(heightMm * this.dpi / 25.4)
    this.commands.push(`^FO${xDots},${yDots}^GB${wDots},${hDots},2^FS`)
    return this
  }

  // Build product label
  buildProductLabel(data: {
    name: string
    price: number
    barcode?: string
    product_code?: string
  }): string {
    const { name, price, barcode, product_code } = data

    this.font('0', 12)
    this.at(2, 1)
    this.text(name.substring(0, 30))

    this.font('0', 24)
    this.at(2, 8)
    this.text(`$${price.toFixed(2)}`)

    this.font('0', 8)
    if (product_code) {
      this.at(2, 12)
      this.text(product_code)
    }

    if (barcode) {
      this.at(2, 14)
      this.barcode128(barcode, 12)
    }

    return this.build()
  }

  // Build bin/location label
  buildBinLabel(data: {
    name: string
    code: string
    barcode?: string
  }): string {
    this.font('0', 24)
    this.at(2, 1)
    this.text(data.name.substring(0, 20))

    this.font('0', 12)
    this.at(2, 7)
    this.text(data.code)

    if (data.barcode) {
      this.at(2, 10)
      this.barcode128(data.barcode, 12)
    }

    return this.build()
  }

  // Build price label (small, for shelf edges)
  buildPriceLabel(data: {
    name: string
    price: number
    barcode?: string
  }): string {
    this.font('0', 10)
    this.at(2, 1)
    this.text(data.name.substring(0, 25))

    this.font('0', 30)
    this.at(2, 6)
    this.text(`$${data.price.toFixed(2)}`)

    if (data.barcode) {
      this.font('0', 8)
      this.at(2, 14)
      this.barcode128(data.barcode, 10)
    }

    return this.build()
  }

  // Build multiple labels (same content, repeated)
  buildMultiple(count: number): string {
    const label = this.commands.join('\n')
    const copies: string[] = []
    for (let i = 0; i < count; i++) {
      copies.push(label)
    }
    return copies.join('\n') + '\n^XZ'
  }

  // Generate final ZPL string
  build(): string {
    this.commands.push(`^XZ`) // End label
    return this.commands.join('\n')
  }
}

// Convenience function
export function createProductLabel(data: {
  name: string
  price: number
  barcode?: string
  product_code?: string
}): string {
  return new ZplBuilder(50, 30).buildProductLabel(data)
}

export function createPriceLabel(data: {
  name: string
  price: number
  barcode?: string
}): string {
  return new ZplBuilder(40, 20).buildPriceLabel(data)
}

export function createBinLabel(data: {
  name: string
  code: string
  barcode?: string
}): string {
  return new ZplBuilder(60, 25).buildBinLabel(data)
}
