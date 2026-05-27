// Ticket data types for receipt generation
export interface TicketData {
  businessName: string
  rfc?: string
  address?: string
  phone?: string
  folio: string
  cashier: string
  date: string
  customer_name?: string
  items: Array<{
    name: string
    quantity: number
    price: number
    total: number
  }>
  subtotal: number
  discount: number
  tax: number
  total: number
  payments: Array<{
    method: string
    amount: number
    reference?: string
  }>
  footer?: string
  policies?: string
}

// HTML receipt template for printing via QZ Tray or browser
export function buildHtmlReceipt(data: TicketData): string {
  const methodLabel = (m: string) => {
    const labels: Record<string, string> = {
      cash: 'Efectivo',
      card: 'Tarjeta',
      transfer: 'Transferencia',
      usd: 'USD',
    }
    return labels[m] || m
  }

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @page { margin: 0; size: 80mm auto; }
    body {
      font-family: 'Courier New', monospace;
      font-size: 12px;
      width: 72mm;
      margin: 0 auto;
      padding: 2mm;
      text-align: center;
    }
    .header { font-size: 18px; font-weight: bold; margin-bottom: 4px; }
    .info { font-size: 11px; margin-bottom: 2px; }
    .divider { border-top: 1px dashed #000; margin: 4px 0; }
    .col-headers { font-weight: bold; text-align: left; font-size: 10px; }
    .item { text-align: left; font-size: 11px; margin: 2px 0; }
    .item-line { display: flex; justify-content: space-between; }
    .totals { text-align: right; margin-top: 4px; }
    .total-line { font-size: 14px; font-weight: bold; }
    .payment { text-align: left; font-size: 11px; }
    .footer { font-size: 10px; margin-top: 8px; }
  </style>
</head>
<body>
  <div class="header">${data.businessName}</div>
  ${data.rfc ? `<div class="info">RFC: ${data.rfc}</div>` : ''}
  ${data.address ? `<div class="info">${data.address}</div>` : ''}
  ${data.phone ? `<div class="info">Tel: ${data.phone}</div>` : ''}
  <div class="divider"></div>
  <div class="info">Folio: ${data.folio}</div>
  <div class="info">Cajero: ${data.cashier}</div>
  <div class="info">Fecha: ${data.date}</div>
  ${data.customer_name ? `<div class="info">Cliente: ${data.customer_name}</div>` : ''}
  <div class="divider"></div>
  <div class="col-headers">CANT  DESCRIPCION               TOTAL</div>
  ${data.items.map(item => `
    <div class="item">
      <div class="item-line">
        <span>${item.quantity.toFixed(0)}x ${item.name.substring(0, 22)}</span>
        <span>$${item.total.toFixed(2)}</span>
      </div>
    </div>
  `).join('')}
  <div class="divider"></div>
  <div class="totals">
    <div>Subtotal: $${data.subtotal.toFixed(2)}</div>
    ${data.discount > 0 ? `<div>Descuento: -$${data.discount.toFixed(2)}</div>` : ''}
    <div>IVA: $${data.tax.toFixed(2)}</div>
    <div class="total-line">TOTAL: $${data.total.toFixed(2)}</div>
  </div>
  <div class="divider"></div>
  <div style="text-align: left; font-size: 11px;">
    <div>METODO PAGO              MONTO</div>
    ${data.payments.map(p => `
      <div>${methodLabel(p.method).padEnd(22)} $${p.amount.toFixed(2)}</div>
    `).join('')}
  </div>
  ${data.footer ? `<div class="divider"></div><div class="footer">${data.footer.replace(/\n/g, '<br>')}</div>` : ''}
  ${data.policies ? `<div class="footer">${data.policies.replace(/\n/g, '<br>')}</div>` : ''}
  <div class="divider"></div>
  <div class="footer">¡Gracias por su compra!</div>
</body>
</html>`
}
