/**
 * Result<T, E> type for functional error handling.
 *
 * A Result represents either success (Ok) or failure (Err),
 * making error handling explicit and eliminating exceptions.
 */

export interface Ok<T> {
  readonly type: 'Ok'
  readonly value: T
}

export interface Err<E> {
  readonly type: 'Err'
  readonly error: E
}

export type Result<T, E> = Ok<T> | Err<E>

// Constructors
export const ok = <T, E = never>(value: T): Result<T, E> => ({
  type: 'Ok',
  value,
})

export const err = <T = never, E = never>(error: E): Result<T, E> => ({
  type: 'Err',
  error,
})

// Type guards
export const isOk = <T, E>(result: Result<T, E>): result is Ok<T> =>
  result.type === 'Ok'

export const isErr = <T, E>(result: Result<T, E>): result is Err<E> =>
  result.type === 'Err'

// Core operations
export const map = <T, U, E>(
  f: (value: T) => U
) => (result: Result<T, E>): Result<U, E> =>
  isOk(result) ? ok(f(result.value)) : result

export const mapErr = <T, E, F>(
  f: (error: E) => F
) => (result: Result<T, E>): Result<T, F> =>
  isErr(result) ? err(f(result.error)) : result

export const flatMap = <T, U, E>(
  f: (value: T) => Result<U, E>
) => (result: Result<T, E>): Result<U, E> =>
  isOk(result) ? f(result.value) : result

export const fold = <T, E, U>(
  onOk: (value: T) => U,
  onErr: (error: E) => U
) => (result: Result<T, E>): U =>
  isOk(result) ? onOk(result.value) : onErr(result.error)

// Utility functions
export const unwrapOr = <T, E>(defaultValue: T) => (result: Result<T, E>): T =>
  isOk(result) ? result.value : defaultValue

export const unwrapOrElse = <T, E>(
  f: (error: E) => T
) => (result: Result<T, E>): T =>
  isOk(result) ? result.value : f(result.error)

// Convert from Promise
export const fromPromise = async <T>(
  promise: Promise<T>
): Promise<Result<T, Error>> => {
  try {
    const value = await promise
    return ok(value)
  } catch (error) {
    return err(error instanceof Error ? error : new Error(String(error)))
  }
}

// Combine multiple Results
export const all = <T, E>(results: Result<T, E>[]): Result<T[], E> => {
  const values: T[] = []
  for (const result of results) {
    if (isErr(result)) return result
    values.push(result.value)
  }
  return ok(values)
}
