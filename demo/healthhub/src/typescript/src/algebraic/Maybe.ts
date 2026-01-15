/**
 * Maybe<T> type for optional values.
 *
 * A Maybe represents either presence (Some) or absence (Nothing),
 * making optional handling explicit without null/undefined.
 */

export interface Some<T> {
  readonly type: 'Some'
  readonly value: T
}

export interface Nothing {
  readonly type: 'Nothing'
}

export type Maybe<T> = Some<T> | Nothing

// Constructors
export const some = <T>(value: T): Maybe<T> => ({
  type: 'Some',
  value,
})

export const nothing = <T = never>(): Maybe<T> => ({
  type: 'Nothing',
})

// Type guards
export const isSome = <T>(maybe: Maybe<T>): maybe is Some<T> =>
  maybe.type === 'Some'

export const isNothing = <T>(maybe: Maybe<T>): maybe is Nothing =>
  maybe.type === 'Nothing'

// Core operations
export const map = <T, U>(
  f: (value: T) => U
) => (maybe: Maybe<T>): Maybe<U> =>
  isSome(maybe) ? some(f(maybe.value)) : nothing()

export const flatMap = <T, U>(
  f: (value: T) => Maybe<U>
) => (maybe: Maybe<T>): Maybe<U> =>
  isSome(maybe) ? f(maybe.value) : nothing()

export const fold = <T, U>(
  onSome: (value: T) => U,
  onNothing: () => U
) => (maybe: Maybe<T>): U =>
  isSome(maybe) ? onSome(maybe.value) : onNothing()

// Utility functions
export const getOrElse = <T>(defaultValue: T) => (maybe: Maybe<T>): T =>
  isSome(maybe) ? maybe.value : defaultValue

export const getOrElseLazy = <T>(
  f: () => T
) => (maybe: Maybe<T>): T =>
  isSome(maybe) ? maybe.value : f()

// Convert from nullable
export const fromNullable = <T>(value: T | null | undefined): Maybe<T> =>
  value != null ? some(value) : nothing()

// Convert to nullable
export const toNullable = <T>(maybe: Maybe<T>): T | null =>
  isSome(maybe) ? maybe.value : null
