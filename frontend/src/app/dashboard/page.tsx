'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api-client'
import { formatCurrency } from '@/lib/utils'
import { ShoppingCart, DollarSign, Package, TrendingUp } from 'lucide-react'

interface DashboardStats {
  today_sales: number
  today_count: number
  today_tickets: number
  low_stock_count: number
  month_sales: number
}

export default function DashboardPage() {
  const router = useRouter()
  const { is_authenticated, role } = useAuthStore()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!is_authenticated) {
      const token = localStorage.getItem('fixit_token')
      if (!token) router.push('/login')
    }
  }, [is_authenticated, router])

  useEffect(() => { loadStats() }, [])

  const loadStats = async () => {
    setLoading(true)
    try {
      const res = await api.get<DashboardStats>('/api/v1/dashboard/summary')
      setStats(res)
    } catch {
      setStats({
        today_sales: 0,
        today_count: 0,
        today_tickets: 0,
        low_stock_count: 0,
        month_sales: 0,
      })
    } finally {
      setLoading(false)
    }
  }

  // Only admin/supervisor can see this
  if (!is_authenticated) return null

  const can_view = role === 'admin' || role === 'supervisor'

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-pos-text">Dashboard</h1>

      {!can_view ? (
        <Card>
          <CardContent className="py-12 text-center text-pos-text-secondary">
            No tienes permisos para ver el dashboard
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={DollarSign}
              label="Ventas Hoy"
              value={stats ? formatCurrency(stats.today_sales) : '—'}
              color="text-emerald-600 bg-emerald-50"
            />
            <StatCard
              icon={ShoppingCart}
              label="Ventas Hoy (cantidad)"
              value={stats ? stats.today_count.toString() : '—'}
              color="text-blue-600 bg-blue-50"
            />
            <StatCard
              icon={TrendingUp}
              label="Ventas del Mes"
              value={stats ? formatCurrency(stats.month_sales) : '—'}
              color="text-purple-600 bg-purple-50"
            />
            <StatCard
              icon={Package}
              label="Stock Bajo"
              value={stats ? stats.low_stock_count.toString() : '—'}
              color="text-amber-600 bg-amber-50"
            />
          </div>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Actividad Reciente</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="py-8 text-center text-sm text-pos-text-secondary">
                  Cargando...
                </div>
              ) : stats && stats.today_count > 0 ? (
                <div className="space-y-2 text-sm text-pos-text-secondary">
                  <p>Hoy se han realizado <strong className="text-pos-text">{stats.today_count}</strong> ventas</p>
                  <p>Total del día: <strong className="text-pos-text">{formatCurrency(stats.today_sales)}</strong></p>
                  <p>Promedio por ticket: <strong className="text-pos-text">
                    {formatCurrency(stats.today_sales / stats.today_count)}
                  </strong></p>
                  <p>Productos con stock bajo: <strong className="text-pos-text">{stats.low_stock_count}</strong></p>
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-pos-text-secondary">
                  No hay ventas hoy
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: string
  color: string
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${color}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div>
          <div className="text-xs text-pos-text-secondary">{label}</div>
          <div className="text-xl font-bold text-pos-text">{value}</div>
        </div>
      </CardContent>
    </Card>
  )
}
