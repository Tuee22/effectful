/**
 * RemoteData<T, E> type for async data states.
 *
 * Represents all possible states of an async operation:
 * - NotAsked: Request not yet made
 * - Loading: Request in progress
 * - Success: Request succeeded with data
 * - Failure: Request failed with error
 */

export interface NotAsked {
  readonly type: 'NotAsked'
}

export interface Loading {
  readonly type: 'Loading'
}

export interface Success<T> {
  readonly type: 'Success'
  readonly data: T
}

export interface Failure<E> {
  readonly type: 'Failure'
  readonly error: E
}

export type RemoteData<T, E> = NotAsked | Loading | Success<T> | Failure<E>

// Constructors
export const notAsked = <T = never, E = never>(): RemoteData<T, E> => ({
  type: 'NotAsked',
})

export const loading = <T = never, E = never>(): RemoteData<T, E> => ({
  type: 'Loading',
})

export const success = <T, E = never>(data: T): RemoteData<T, E> => ({
  type: 'Success',
  data,
})

export const failure = <T = never, E = never>(error: E): RemoteData<T, E> => ({
  type: 'Failure',
  error,
})

// Type guards
export const isNotAsked = <T, E>(rd: RemoteData<T, E>): rd is NotAsked =>
  rd.type === 'NotAsked'

export const isLoading = <T, E>(rd: RemoteData<T, E>): rd is Loading =>
  rd.type === 'Loading'

export const isSuccess = <T, E>(rd: RemoteData<T, E>): rd is Success<T> =>
  rd.type === 'Success'

export const isFailure = <T, E>(rd: RemoteData<T, E>): rd is Failure<E> =>
  rd.type === 'Failure'

// Core operations
export const map = <T, U, E>(
  f: (data: T) => U
) => (rd: RemoteData<T, E>): RemoteData<U, E> =>
  isSuccess(rd) ? success(f(rd.data)) : rd

export const mapError = <T, E, F>(
  f: (error: E) => F
) => (rd: RemoteData<T, E>): RemoteData<T, F> => {
  switch (rd.type) {
    case 'NotAsked':
      return notAsked()
    case 'Loading':
      return loading()
    case 'Success':
      return success(rd.data)
    case 'Failure':
      return failure(f(rd.error))
  }
}

export const flatMap = <T, U, E>(
  f: (data: T) => RemoteData<U, E>
) => (rd: RemoteData<T, E>): RemoteData<U, E> =>
  isSuccess(rd) ? f(rd.data) : rd

export const fold = <T, E, U>(
  onNotAsked: () => U,
  onLoading: () => U,
  onSuccess: (data: T) => U,
  onFailure: (error: E) => U
) => (rd: RemoteData<T, E>): U => {
  switch (rd.type) {
    case 'NotAsked':
      return onNotAsked()
    case 'Loading':
      return onLoading()
    case 'Success':
      return onSuccess(rd.data)
    case 'Failure':
      return onFailure(rd.error)
  }
}

// Utility functions
export const getOrElse = <T, E>(defaultValue: T) => (rd: RemoteData<T, E>): T =>
  isSuccess(rd) ? rd.data : defaultValue

export const toMaybe = <T, E>(rd: RemoteData<T, E>): import('./Maybe').Maybe<T> =>
  isSuccess(rd) ? { type: 'Some', value: rd.data } : { type: 'Nothing' }
