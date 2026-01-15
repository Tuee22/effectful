/**
 * Validated<T, E> type for form validation.
 *
 * A Validated represents either a valid value or accumulated errors.
 * Unlike Result, errors accumulate instead of short-circuiting.
 */

export interface Valid<T> {
  readonly type: 'Valid'
  readonly value: T
}

export interface Invalid<E> {
  readonly type: 'Invalid'
  readonly errors: readonly E[]
}

export type Validated<T, E> = Valid<T> | Invalid<E>

// Constructors
export const valid = <T, E = never>(value: T): Validated<T, E> => ({
  type: 'Valid',
  value,
})

export const invalid = <T = never, E = never>(errors: readonly E[]): Validated<T, E> => ({
  type: 'Invalid',
  errors,
})

export const invalidSingle = <T = never, E = never>(error: E): Validated<T, E> => ({
  type: 'Invalid',
  errors: [error],
})

// Type guards
export const isValid = <T, E>(v: Validated<T, E>): v is Valid<T> =>
  v.type === 'Valid'

export const isInvalid = <T, E>(v: Validated<T, E>): v is Invalid<E> =>
  v.type === 'Invalid'

// Core operations
export const map = <T, U, E>(
  f: (value: T) => U
) => (v: Validated<T, E>): Validated<U, E> =>
  isValid(v) ? valid(f(v.value)) : v

export const mapErrors = <T, E, F>(
  f: (error: E) => F
) => (v: Validated<T, E>): Validated<T, F> =>
  isInvalid(v) ? invalid(v.errors.map(f)) : v

export const fold = <T, E, U>(
  onValid: (value: T) => U,
  onInvalid: (errors: readonly E[]) => U
) => (v: Validated<T, E>): U =>
  isValid(v) ? onValid(v.value) : onInvalid(v.errors)

// Combine multiple Validated values (accumulates errors)
export const combine = <T extends readonly Validated<unknown, E>[], E>(
  ...vs: T
): Validated<{ [K in keyof T]: T[K] extends Validated<infer U, E> ? U : never }, E> => {
  const errors: E[] = []
  const values: unknown[] = []

  for (const v of vs) {
    if (isInvalid(v)) {
      errors.push(...v.errors)
    } else {
      values.push(v.value)
    }
  }

  if (errors.length > 0) {
    return invalid(errors) as Validated<{ [K in keyof T]: T[K] extends Validated<infer U, E> ? U : never }, E>
  }

  return valid(values as { [K in keyof T]: T[K] extends Validated<infer U, E> ? U : never })
}

// Validation helpers for common patterns
export const validateRequired = <E>(error: E) => (value: string): Validated<string, E> =>
  value.trim().length > 0 ? valid(value) : invalidSingle(error)

export const validateMinLength = <E>(minLength: number, error: E) => (value: string): Validated<string, E> =>
  value.length >= minLength ? valid(value) : invalidSingle(error)

export const validateEmail = <E>(error: E) => (value: string): Validated<string, E> => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(value) ? valid(value) : invalidSingle(error)
}
