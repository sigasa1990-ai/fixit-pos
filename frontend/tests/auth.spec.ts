import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test('should show login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('h1')).toContainText(/login|entrar|iniciar/i)
  })

  test('should redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/pos')
    await page.waitForURL('/login')
    expect(page.url()).toContain('/login')
  })

  test('should show PIN input on login page', async ({ page }) => {
    await page.goto('/login')
    await expect(page.locator('input[type="password"], input[type="tel"], input[name="pin"]').first()).toBeVisible()
  })

  test('should have a numpad on login page', async ({ page }) => {
    await page.goto('/login')
    // Look for digit buttons
    const digits = page.locator('button, [role="button"]').filter({ hasText: /^[0-9]$/ })
    const count = await digits.count()
    expect(count).toBeGreaterThanOrEqual(10) // 0-9
  })
})

test.describe('Session Persistence', () => {
  test('should restore auth state from localStorage', async ({ page }) => {
    // Set up localStorage with a fake token before navigating
    await page.goto('/login')
    await page.evaluate(() => {
      const fakePayload = {
        sub: 'user-1',
        tenant_id: 'tenant-1',
        role: 'admin',
        permissions: ['sale.create', 'sale.read'],
        full_name: 'Test User',
      }
      const token = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })) + '.' +
                    btoa(JSON.stringify(fakePayload)) + '.fakesignature'
      localStorage.setItem('fixit_token', token)
    })
    await page.goto('/')
    // Should not redirect to login since token exists
    await page.waitForTimeout(1000)
    expect(page.url()).not.toContain('/login')
  })
})
