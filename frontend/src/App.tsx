import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { RequireAuth } from './features/auth/RequireAuth'
import { CreateTicketPage } from './routes/CreateTicketPage'
import { DashboardPage } from './routes/DashboardPage'
import { ForgotPasswordPage } from './routes/ForgotPasswordPage'
import { HomePage } from './routes/HomePage'
import { LoginPage } from './routes/LoginPage'
import { NotFoundPage } from './routes/NotFoundPage'
import { RegisterPage } from './routes/RegisterPage'
import { ResetPasswordPage } from './routes/ResetPasswordPage'
import { TicketDetailPage } from './routes/TicketDetailPage'
import { TicketsPage } from './routes/TicketsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="reset-password" element={<ResetPasswordPage />} />
        <Route element={<RequireAuth />}>
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="tickets" element={<TicketsPage />} />
          <Route path="tickets/new" element={<CreateTicketPage />} />
          <Route path="tickets/:id" element={<TicketDetailPage />} />
        </Route>
        <Route path="signin" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
