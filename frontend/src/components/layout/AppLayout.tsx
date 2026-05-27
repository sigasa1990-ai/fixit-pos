'use client'

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { Sidebar } from './Sidebar'
import { useAuthStore } from '@/stores/auth-store'

export function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { is_authenticated } = useAuthStore()

  useEffect(() => {
    const token = localStorage.getItem('fixit_token')
    if (!token && pathname !== '/login') {
      router.push('/login')
    }
  }, [pathname, router])

  if (pathname === '/login') {
    return <>{children}</>
  }

  return (
    <div className="flex h-screen overflow-hidden bg-pos-background">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
