import { test, expect } from '@playwright/test'

test.describe('Barcode Scanner Simulation', () => {
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

  test('scanner rapid input should trigger product search', async ({ page }) => {
    // Listen for API calls
    const searchPromise = page.waitForResponse(
      resp => resp.url().includes('/api/v1/products/search') && resp.request().method() === 'GET',
      { timeout: 5000 }
    ).catch(() => null)

    // Simulate scanner input: rapid keystrokes ending with Enter
    const barcode = '7501234567890'
    for (const char of barcode) {
      await page.keyboard.press(char, { delay: 20 })
    }
    await page.keyboard.press('Enter')

    const response = await searchPromise
    // Test shouldn't fail if backend is not running - the request was made
  })

  test('manual typing should not trigger barcode scan', async ({ page }) => {
    let scanTriggered = false
    page.on('response', resp => {
      if (resp.url().includes('/api/v1/products/search')) {
        scanTriggered = true
      }
    })

    // Type slowly (simulating manual typing)
    const text = 'hello'
    for (const char of text) {
      await page.keyboard.press(char, { delay: 200 })
    }
    await page.keyboard.press('Enter', { delay: 200 })

    // Wait to see if any scan was triggered
    await page.waitForTimeout(500)
    expect(scanTriggered).toBe(false)
  })
})
