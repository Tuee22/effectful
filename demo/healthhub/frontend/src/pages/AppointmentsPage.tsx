/**
 * AppointmentsPage - Appointments list page.
 */

import { useAppointments } from '../hooks/useAppointments'
import { RemoteDataRenderer } from '../components/common/RemoteDataRenderer'
import { AppointmentList } from '../components/appointments/AppointmentList'
import './AppointmentsPage.css'

export const AppointmentsPage = () => {
  const { appointmentList } = useAppointments()

  return (
    <div className="appointments-page" data-state={appointmentList.type}>
      <div className="page-header">
        <h1>Appointments</h1>
      </div>

      <RemoteDataRenderer
        data={appointmentList}
        notAsked={() => (
          <p className="page-empty">
            No appointments loaded. Refresh the page to load appointments.
          </p>
        )}
        success={(appointments) => <AppointmentList appointments={appointments} />}
      />
    </div>
  )
}
