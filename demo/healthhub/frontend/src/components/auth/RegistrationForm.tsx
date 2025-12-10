import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import './LoginForm.css'

interface RegistrationData {
  email: string
  password: string
  confirmPassword: string
  firstName: string
  lastName: string
  dateOfBirth: string
  phone: string
  bloodType: string
  allergies: string
  emergencyContact: string
  insuranceId: string
  address: string
}

const initialFormData: RegistrationData = {
  email: '',
  password: '',
  confirmPassword: '',
  firstName: '',
  lastName: '',
  dateOfBirth: '',
  phone: '',
  bloodType: '',
  allergies: '',
  emergencyContact: '',
  insuranceId: '',
  address: '',
}

export const RegistrationForm = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState<RegistrationData>(initialFormData)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }))
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validate password confirmation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Validate required fields
    if (
      !formData.email ||
      !formData.password ||
      !formData.firstName ||
      !formData.lastName ||
      !formData.dateOfBirth ||
      !formData.emergencyContact
    ) {
      setError('Please fill in all required fields')
      return
    }

    setIsSubmitting(true)

    try {
      // Parse allergies from comma-separated string to array
      const allergiesArray = formData.allergies
        .split(',')
        .map((a) => a.trim())
        .filter((a) => a.length > 0)

      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          role: 'patient',
          first_name: formData.firstName,
          last_name: formData.lastName,
          date_of_birth: formData.dateOfBirth,
          phone: formData.phone || null,
          blood_type: formData.bloodType || null,
          allergies: allergiesArray,
          emergency_contact: formData.emergencyContact,
          insurance_id: formData.insuranceId || null,
          address: formData.address || null,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        setError(data.detail || 'Registration failed')
        setIsSubmitting(false)
        return
      }

      // Success - redirect to login page
      navigate('/login', {
        state: { message: data.message || 'Registration successful. Please log in.' }
      })
    } catch (err) {
      setError('Network error. Please try again.')
      setIsSubmitting(false)
    }
  }

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <h2 className="login-title">Register for HealthHub</h2>
      {error && <div className="login-error">{error}</div>}

      <div className="form-group">
        <label htmlFor="email">
          Email <span className="required">*</span>
        </label>
        <input
          id="email"
          name="email"
          type="email"
          value={formData.email}
          onChange={handleChange}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="password">
          Password <span className="required">*</span>
        </label>
        <input
          id="password"
          name="password"
          type="password"
          value={formData.password}
          onChange={handleChange}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="confirmPassword">
          Confirm Password <span className="required">*</span>
        </label>
        <input
          id="confirmPassword"
          name="confirmPassword"
          type="password"
          value={formData.confirmPassword}
          onChange={handleChange}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="firstName">
          First Name <span className="required">*</span>
        </label>
        <input
          id="firstName"
          name="firstName"
          type="text"
          value={formData.firstName}
          onChange={handleChange}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="lastName">
          Last Name <span className="required">*</span>
        </label>
        <input
          id="lastName"
          name="lastName"
          type="text"
          value={formData.lastName}
          onChange={handleChange}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="dateOfBirth">
          Date of Birth <span className="required">*</span>
        </label>
        <input
          id="dateOfBirth"
          name="dateOfBirth"
          type="date"
          value={formData.dateOfBirth}
          onChange={handleChange}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="emergencyContact">
          Emergency Contact <span className="required">*</span>
        </label>
        <input
          id="emergencyContact"
          name="emergencyContact"
          type="text"
          placeholder="Name: Phone"
          value={formData.emergencyContact}
          onChange={handleChange}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="phone">Phone</label>
        <input
          id="phone"
          name="phone"
          type="tel"
          placeholder="555-0199"
          value={formData.phone}
          onChange={handleChange}
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="bloodType">Blood Type</label>
        <input
          id="bloodType"
          name="bloodType"
          type="text"
          placeholder="O+, A-, etc."
          value={formData.bloodType}
          onChange={handleChange}
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="allergies">Allergies (comma-separated)</label>
        <input
          id="allergies"
          name="allergies"
          type="text"
          placeholder="Penicillin, Peanuts"
          value={formData.allergies}
          onChange={handleChange}
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="insuranceId">Insurance ID</label>
        <input
          id="insuranceId"
          name="insuranceId"
          type="text"
          value={formData.insuranceId}
          onChange={handleChange}
          disabled={isSubmitting}
        />
      </div>

      <div className="form-group">
        <label htmlFor="address">Address</label>
        <input
          id="address"
          name="address"
          type="text"
          placeholder="123 Main St, City, State ZIP"
          value={formData.address}
          onChange={handleChange}
          disabled={isSubmitting}
        />
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Registering...' : 'Register'}
      </button>

      <div className="form-footer">
        <Link to="/login">Already have an account? Sign in</Link>
      </div>
    </form>
  )
}
