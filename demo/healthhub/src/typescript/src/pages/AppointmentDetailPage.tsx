/**
 * AppointmentDetailPage - Individual appointment detail page.
 */

import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAppointments } from '../hooks/useAppointments'
import { RemoteDataRenderer } from '../components/common/RemoteDataRenderer'
import { AppointmentDetail } from '../components/appointments/AppointmentDetail'
import './AppointmentDetailPage.css'

export const AppointmentDetailPage = () => {
  const { id: appointmentId } = useParams<{ id: string }>()
  const { currentAppointment, fetchAppointment, transitionStatus } = useAppointments()

  useEffect(() => {
    if (appointmentId) {
      fetchAppointment(appointmentId)
    }
  }, [appointmentId, fetchAppointment])

  const handleTransition = async (newStatus: string) => {
    if (appointmentId) {
      await transitionStatus(appointmentId, newStatus)
    }
  }

  return (
    <div className="appointment-detail-page" data-state={currentAppointment.type}>
      <div className="page-header">
        <Link to="/appointments" className="back-link">
          &larr; Back to Appointments
        </Link>
        <h1>Appointment Details</h1>
      </div>

      <RemoteDataRenderer
        data={currentAppointment}
        notAsked={() => <p>Loading appointment...</p>}
        success={(appointment) => (
          <AppointmentDetail
            appointment={appointment}
            onTransition={handleTransition}
          />
        )}
      />
    </div>
  )
}
