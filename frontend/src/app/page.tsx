'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem('fixit_token')
    if (token) {
      router.push('/pos')
    } else {
      router.push('/login')
    }
  }, [router])

  return null
}
