import { test, expect } from '@playwright/test'

test.describe('POS Page', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authenticated state
    await page.goto('/login')
    await page.evaluate(() => {
      const fakePayload = {
        sub: 'user-1',
        tenant_id: 'tenant-1',
        role: 'admin',
        permissions: ['sale.create', 'sale.read', 'sale.cancel'],
        full_name: 'Test Cashier',
      }
      const token = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })) + '.' +
                    btoa(JSON.stringify(fakePayload)) + '.fakesignature'
      localStorage.setItem('fixit_token', token)
    })
    await page.goto('/pos')
  })

  test('should render POS page', async ({ page }) => {
    await expect(page.locator('h1')).toContainText(/POS/i)
  })

  test('should show product search input', async ({ page }) => {
    await expect(page.locator('input[placeholder*="buscar" i], input[type="search"]').first()).toBeVisible()
  })

  test('should show cart panel', async ({ page }) => {
    await expect(page.locator('text=Venta Actual, text=Carrito').first()).toBeVisible()
  })

  test('should create initial order tab', async ({ page }) => {
    await expect(page.locator('[role="tab"], .order-tab, [class*="tab"]').first()).toBeVisible()
  })

  test('should show cash register selector', async ({ page }) => {
    await expect(page.locator('select').first()).toBeVisible()
  })

  test('should show printer status indicator', async ({ page }) => {
    await expect(page.locator('[title*="Impresora" i], [title*="Conectar" i]').first()).toBeVisible()
  })

  test('should show scanner indicator', async ({ page }) => {
    await expect(page.locator('[title*="Escáner" i]').first()).toBeVisible()
  })

  test('should show keyboard shortcut help button', async ({ page }) => {
    await expect(page.locator('[title*="Atajos" i]').first()).toBeVisible()
  })

  test('should show username in header', async ({ page }) => {
    await expect(page.locator('text=Test Cashier')).toBeVisible()
  })
})

test.describe('Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.evaluate(() => {
      const fakePayload = {
        sub: 'user-1',
        tenant_id: 'tenant-1',
        role: 'admin',
        permissions: ['sale.create', 'sale.read'],
        full_name: 'Test',
      }
      const token = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })) + '.' +
                    btoa(JSON.stringify(fakePayload)) + '.fakesignature'
      localStorage.setItem('fixit_token', token)
    })
    await page.goto('/pos')
  })

  test('Ctrl+/ should open shortcut help', async ({ page }) => {
    await page.keyboard.press('Control+/')
    await expect(page.locator('text=Atajos').first()).toBeVisible()
  })

  test('Escape should close shortcut help modal', async ({ page }) => {
    await page.keyboard.press('Control+/')
    await expect(page.locator('text=Atajos').first()).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.locator('text=Atajos').first()).not.toBeVisible()
  })

  test('F11 should clear active order', async ({ page }) => {
    // Clear should show a toast or clear the cart
    await page.keyboard.press('F11')
    // Should show "Venta limpiada" toast
    await expect(page.locator('text=limpiada').first()).toBeVisible()
  })

  test('F2 should focus search input', async ({ page }) => {
    await page.keyboard.press('F2')
    const searchInput = page.locator('input[placeholder*="buscar" i], input[type="search"]').first()
    await expect(searchInput).toBeFocused()
  })
})
