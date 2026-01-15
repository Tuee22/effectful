import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import './PrescriptionForm.css'

interface Patient {
  id: string
  first_name: string
  last_name: string
}

interface PrescriptionFormData {
  patientId: string
  medication: string
  dosage: string
  frequency: string
  durationDays: string
  refills: string
  notes: string
}

interface PrescriptionFormProps {
  onSuccess: () => void
  onCancel: () => void
}

const initialFormData: PrescriptionFormData = {
  patientId: '',
  medication: '',
  dosage: '',
  frequency: '',
  durationDays: '30',
  refills: '0',
  notes: '',
}

export const PrescriptionForm = ({ onSuccess, onCancel }: PrescriptionFormProps) => {
  const { getValidAccessToken, userId } = useAuth()
  const [formData, setFormData] = useState<PrescriptionFormData>(initialFormData)
  const [patients, setPatients] = useState<Patient[]>([])
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingPatients, setIsLoadingPatients] = useState(true)

  // Fetch patients list on mount
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const token = await getValidAccessToken()
        if (!token) {
          setError('Authentication required')
          setIsLoadingPatients(false)
          return
        }

        const response = await fetch('/api/patients/', {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (!response.ok) {
          throw new Error('Failed to load patients')
        }

        const data = await response.json()
        setPatients(data)
        setIsLoadingPatients(false)
      } catch (err) {
        setError('Failed to load patients list')
        setIsLoadingPatients(false)
      }
    }

    void fetchPatients()
  }, [getValidAccessToken])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }))
    setError(null)
    setWarning(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setWarning(null)

    // Validate required fields
    if (
      !formData.patientId ||
      !formData.medication ||
      !formData.dosage ||
      !formData.frequency ||
      !formData.durationDays ||
      !formData.refills
    ) {
      setError('Please fill in all required fields')
      return
    }

    setIsSubmitting(true)

    try {
      const token = await getValidAccessToken()
      if (!token) {
        setError('Authentication required')
        setIsSubmitting(false)
        return
      }

      const response = await fetch('/api/prescriptions/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          patient_id: formData.patientId,
          doctor_id: userId,
          medication: formData.medication,
          dosage: formData.dosage,
          frequency: formData.frequency,
          duration_days: parseInt(formData.durationDays, 10),
          refills_remaining: parseInt(formData.refills, 10),
          notes: formData.notes || null,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        // Check for allergy/interaction warnings
        if (data.warnings) {
          setWarning(data.warnings.join('; '))
        }
        setError(data.detail || 'Failed to create prescription')
        setIsSubmitting(false)
        return
      }

      // Success
      onSuccess()
    } catch (err) {
      setError('Network error. Please try again.')
      setIsSubmitting(false)
    }
  }

  if (isLoadingPatients) {
    return (
      <div className="prescription-form-modal">
        <div className="prescription-form">
          <p>Loading patients...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="prescription-form-modal">
      <div className="prescription-form">
        <h2>Create Prescription</h2>

        {error && <div className="form-error">{error}</div>}
        {warning && <div className="form-warning">{warning}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="patientId">
              Patient <span className="required">*</span>
            </label>
            <select
              id="patientId"
              name="patientId"
              value={formData.patientId}
              onChange={handleChange}
              required
              disabled={isSubmitting}
            >
              <option value="">Select a patient</option>
              {patients.map((patient) => (
                <option key={patient.id} value={patient.id}>
                  {patient.first_name} {patient.last_name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="medication">
              Medication <span className="required">*</span>
            </label>
            <input
              id="medication"
              name="medication"
              type="text"
              value={formData.medication}
              onChange={handleChange}
              placeholder="e.g., Lisinopril"
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="dosage">
              Dosage <span className="required">*</span>
            </label>
            <input
              id="dosage"
              name="dosage"
              type="text"
              value={formData.dosage}
              onChange={handleChange}
              placeholder="e.g., 10mg"
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="frequency">
              Frequency <span className="required">*</span>
            </label>
            <input
              id="frequency"
              name="frequency"
              type="text"
              value={formData.frequency}
              onChange={handleChange}
              placeholder="e.g., Once daily"
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="durationDays">
                Duration (days) <span className="required">*</span>
              </label>
              <input
                id="durationDays"
                name="durationDays"
                type="number"
                value={formData.durationDays}
                onChange={handleChange}
                min="1"
                required
                disabled={isSubmitting}
              />
            </div>

            <div className="form-group">
              <label htmlFor="refills">
                Refills <span className="required">*</span>
              </label>
              <input
                id="refills"
                name="refills"
                type="number"
                value={formData.refills}
                onChange={handleChange}
                min="0"
                required
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              placeholder="Special instructions (optional)"
              rows={3}
              disabled={isSubmitting}
            />
          </div>

          <div className="form-actions">
            <button type="button" className="cancel-button" onClick={onCancel} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" className="submit-button" disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Prescription'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
