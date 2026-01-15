/**
 * Algebraic Data Types for HealthHub frontend.
 *
 * Re-exports all ADT types and utilities.
 * Uses explicit re-exports to avoid name conflicts.
 */

// Result types and utilities
export type { Ok, Err, Result } from './Result'
export { ok, err, isOk, isErr } from './Result'
export {
  map as mapResult,
  flatMap as flatMapResult,
  fold as foldResult,
  unwrapOr as unwrapOrResult,
  unwrapOrElse as unwrapOrElseResult,
} from './Result'

// Maybe types and utilities
export type { Some, Nothing, Maybe } from './Maybe'
export { some, nothing, isSome, isNothing } from './Maybe'
export {
  map as mapMaybe,
  flatMap as flatMapMaybe,
  fold as foldMaybe,
  getOrElse as getOrElseMaybe,
  fromNullable,
} from './Maybe'

// RemoteData types and utilities
export type { NotAsked, Loading, Success, Failure, RemoteData } from './RemoteData'
export { notAsked, loading, success, failure, isNotAsked, isLoading, isSuccess, isFailure } from './RemoteData'
export {
  map as mapRemoteData,
  fold as foldRemoteData,
} from './RemoteData'

// Validated types and utilities
export type { Valid, Invalid, Validated } from './Validated'
export { valid, invalid, invalidSingle, isValid, isInvalid } from './Validated'
export {
  map as mapValidated,
  fold as foldValidated,
  combine as combineValidated,
} from './Validated'
