/**
 * AppointmentForm component - Create appointment form.
 */

import { useState } from 'react'
import './AppointmentForm.css'

interface AppointmentFormProps {
  readonly patientId?: string
  readonly doctorId?: string
  readonly onSubmit: (data: {
    patient_id: string
    doctor_id: string
    reason: string
  }) => Promise<boolean>
}

export const AppointmentForm = ({
  patientId: initialPatientId = '',
  doctorId: initialDoctorId = '',
  onSubmit,
}: AppointmentFormProps) => {
  const [patientId, setPatientId] = useState(initialPatientId)
  const [doctorId, setDoctorId] = useState(initialDoctorId)
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    const success = await onSubmit({
      patient_id: patientId,
      doctor_id: doctorId,
      reason,
    })

    if (!success) {
      setError('Failed to create appointment. Please try again.')
    }

    setIsSubmitting(false)
  }

  return (
    <form className="appointment-form" onSubmit={handleSubmit}>
      <h3>Schedule Appointment</h3>

      {error && <div className="form-error">{error}</div>}

      <div className="form-group">
        <label htmlFor="patientId">Patient ID</label>
        <input
          id="patientId"
          type="text"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          placeholder="Enter patient ID"
          required
          disabled={isSubmitting || !!initialPatientId}
        />
      </div>

      <div className="form-group">
        <label htmlFor="doctorId">Doctor ID</label>
        <input
          id="doctorId"
          type="text"
          value={doctorId}
          onChange={(e) => setDoctorId(e.target.value)}
          placeholder="Enter doctor ID"
          required
          disabled={isSubmitting || !!initialDoctorId}
        />
      </div>

      <div className="form-group">
        <label htmlFor="reason">Reason</label>
        <textarea
          id="reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Enter reason for appointment"
          required
          disabled={isSubmitting}
          rows={3}
        />
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Scheduling...' : 'Schedule Appointment'}
      </button>
    </form>
  )
}
