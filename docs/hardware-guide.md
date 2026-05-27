# FIXIT POS — Hardware Guide (Stage 5)

## Arquitectura de Hardware

```
┌─────────────────────────────────────────────────────────┐
│                    PC/Cajero (Browser)                     │
│                                                           │
│  ┌─────────────────────┐     ┌─────────────────────────┐  │
│  │   FIXIT POS WebApp  │     │    QZ Tray (Local)      │  │
│  │   (Next.js)         │◄───►│    WebSocket localhost   │  │
│  │                     │     │    Puerto 8181           │  │
│  └─────────────────────┘     └──────────┬──────────────┘  │
│                                          │                  │
│  ┌─────────────────────┐                │                  │
│  │  Escáner USB HID    │   (Keyboard    │                  │
│  │  (Plug & Play)      │    emulation)  │                  │
│  └─────────────────────┘                │                  │
│                                          ▼                  │
│                              ┌─────────────────────────┐  │
│                              │   Impresora Térmica      │  │
│                              │   (USB / Ethernet)       │  │
│                              │   ESC/POS Protocol       │  │
│                              └─────────────────────────┘  │
│                                          │                  │
│                                          ▼                  │
│                              ┌─────────────────────────┐  │
│                              │   Cajón de Dinero        │  │
│                              │   (RJ11/RJ12 - Drawer)   │  │
│                              └─────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 1. QZ Tray

### ¿Qué es?
QZ Tray es una aplicación de escritorio que permite la comunicación con hardware POS (impresoras térmicas, cajones de dinero, escáneres) desde una aplicación web a través de WebSocket.

### Instalación
1. Descargar QZ Tray desde: https://qz.io/download/
2. Instalar el programa (Windows, macOS, Linux)
3. Iniciar QZ Tray (debe quedar ejecutándose en segundo plano)
4. Verificar que el icono de QZ Tray aparece en la bandeja del sistema

### Configuración
- Puerto por defecto: 8181 (WebSocket)
- No requiere configuración adicional para funcionar con FIXIT POS
- El frontend se conecta automáticamente al detectar QZ Tray

### Seguridad
Por defecto, QZ Tray solo acepta conexiones desde `localhost`. Para producción:
1. Configurar SSL en QZ Tray
2. Usar `wss://localhost:8182` para conexiones seguras
3. Configurar la firma digital en QZ Tray para sitios específicos

---

## 2. Impresora Térmica (ESC/POS)

### Compatibilidad
| Marca | Modelos | Protocolo |
|-------|---------|-----------|
| Epson | TM-T20, TM-T88, TM-m30 | ESC/POS |
| Xprinter | XP-58, XP-80, XP-Q80 | ESC/POS |
| Star | TSP100, SP700 | ESC/POS |
| Bixolon | SRP-350, SRP-275 | ESC/POS |
| Zebra | GK420d, ZD420 (thermal) | ESC/POS / ZPL |

### Conexión
1. Conectar la impresora vía USB a la PC del cajero
2. La impresora debe instalarse como impresora predeterminada de Windows
3. QZ Tray detecta automáticamente las impresoras disponibles
4. En FIXIT POS, ir a Configuración → Hardware → Seleccionar impresora

### Especificaciones Recomendadas
- Ancho de papel: 80mm o 58mm
- Resolución: 203 DPI
- Velocidad: ≥ 250mm/s
- Interface: USB + Serial

### Ancho de Ticket
- 80mm → 42 columnas de texto
- 58mm → 32 columnas de texto

---

## 3. Cajón de Dinero

### Compatibilidad
| Tipo | Conexión | Funciona con |
|------|----------|--------------|
| RJ11/RJ12 | Puerto drawer de la impresora | Impresoras Epson, Star, Bixolon |
| USB | Puerto USB directo | Cajones USB genéricos |

### Configuración
1. Conectar el cajón al puerto "Drawer" de la impresora térmica (RJ11/RJ12)
2. El comando ESC/POS `ESC p 0 25 250` abre el cajón automáticamente
3. FIXIT POS abre el cajón automáticamente al cobrar en efectivo

### Comandos Soportados
- Pin 2 (estándar): `1B 70 00 19 FA`
- Pin 5 (alternativo): `1B 70 01 19 FA`

---

## 4. Escáner de Código de Barras

### Compatibilidad
Cualquier escáner USB HID que emule teclado es compatible.

### Marcas Recomendadas
- Honeywell (MS9520, MS9540, Voyager)
- Zebra (LS2208, DS2208)
- Datalogic (QuickScan, Gryphon)
- Generic USB barcode scanners

### Configuración
1. Conectar el escáner vía USB
2. El sistema operativo lo reconoce como teclado
3. NO requiere configuración adicional en FIXIT POS
4. El escáner funciona inmediatamente

### Formatos de Código de Barras Soportados
- Code 128
- EAN-13 (estándar México)
- EAN-8
- UPC-A
- UPC-E
- Código de producto (alfanumérico)

### Notas Técnicas
- El escáner envía los caracteres seguidos de un Enter
- FIXIT POS detecta la ráfaga de caracteres y la diferencia del tecleo humano
- La búsqueda se activa automáticamente al escanear
- Si el código de barras tiene 8+ dígitos, se busca automáticamente
- Los escáneres se pueden configurar para agregar o no el prefijo/sufijo

---

## 5. Impresora de Etiquetas (Barcode Labels)

### Compatibilidad
| Marca | Protocolo |
|-------|-----------|
| Zebra | ZPL (Zebra Programming Language) |
| TSC | ZPL-compatible |
| Brother | ZPL / Raster |
| Xprinter | ZPL / ESC/POS |

### Formatos Generados por FIXIT POS
| Tipo | Tamaño | Contenido |
|------|--------|-----------|
| Producto | 50mm x 30mm | Nombre, precio, código de barras |
| Precio | 40mm x 20mm | Nombre, precio grande, código de barras |
| Ubicación/Bin | 60mm x 25mm | Nombre, código, código de barras |

### Prueba de Etiquetas
1. Ir a Configuración → Hardware → Impresión de Etiquetas
2. Ingresar código de barras de prueba
3. Seleccionar "Etiqueta Producto" o "Etiqueta Precio"
4. La etiqueta se imprime en la impresora seleccionada

---

## 6. Flujo de Impresión Automática

Cuando se completa una venta en el POS:

```
1. Venta exitosa → API responde con datos de venta
2. Frontend obtiene datos completos de la venta (GET /api/v1/sales/{id})
3. Frontend construye ticket ESC/POS con:
   - Encabezado (nombre del negocio, RFC, dirección)
   - Folio, cajero, fecha
   - Cliente (si aplica)
   - Lista de productos (cantidad, descripción, precio)
   - Subtotal, IVA, descuento, total
   - Métodos de pago
   - Pie (políticas, agradecimiento)
4. Envía a QZ Tray → Impresora térmica
5. Si el pago fue en efectivo → Abre cajón de dinero
```

### Configuración de Impresión
- La impresión automática se activa/desactiva desde Configuración
- Se puede seleccionar la impresora predeterminada
- El cajón se abre solo para pagos en efectivo

---

## 7. Solución de Problemas

| Problema | Causa | Solución |
|----------|-------|----------|
| QZ Tray no conecta | QZ Tray no está instalado | Descargar e instalar desde qz.io |
| QZ Tray no conecta | Puerto 8181 bloqueado | Verificar firewall |
| No hay impresoras | Impresora no conectada | Conectar impresora USB |
| No hay impresoras | Controladores no instalados | Instalar drivers de la impresora |
| Ticket en blanco | Formato incorrecto | Verificar que la impresora soporte ESC/POS |
| Cajón no abre | Conexión incorrecta | Verificar cable RJ11 al puerto drawer |
| Escáner no funciona | Puerto USB | Probar otro puerto USB |
| Escáner no funciona | Configuración | Escanear código de configuración del fabricante |
| Etiqueta no imprime | Protocolo incorrecto | Usar impresora ZPL-compatible |

---

## 8. Hardware Recomendado (México)

| Componente | Modelo Recomendado | Precio Aprox. |
|------------|-------------------|---------------|
| Impresora Térmica 80mm | Xprinter XP-Q80II | $1,500 MXN |
| Impresora Térmica 58mm | Xprinter XP-58IIH | $900 MXN |
| Impresora Térmica | Epson TM-T20X | $3,500 MXN |
| Cajón de Dinero | APG Vasco 1006 | $1,200 MXN |
| Escáner Código Barras | Honeywell MS9540 | $1,800 MXN |
| Escáner Código Barras | Zebra LS2208 | $2,200 MXN |
| Impresora Etiquetas | Zebra GK420d | $4,500 MXN |
| Impresora Etiquetas | TSC TDP-225 | $3,500 MXN |
| Monitor Táctil | Elo 15" Touch | $4,000 MXN |
| Cajón Todo-en-uno | POS All-in-one 15" | $8,000 MXN |
