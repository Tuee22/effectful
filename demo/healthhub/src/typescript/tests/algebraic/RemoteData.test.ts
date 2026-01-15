import { describe, it, expect } from 'vitest'
import {
  notAsked,
  loading,
  success,
  failure,
  isNotAsked,
  isLoading,
  isSuccess,
  isFailure,
  map,
  mapError,
  flatMap,
  fold,
  getOrElse,
  toMaybe,
} from '../../src/algebraic/RemoteData'

describe('RemoteData', () => {
  describe('constructors', () => {
    it('notAsked creates NotAsked variant', () => {
      const rd = notAsked()
      expect(rd.type).toBe('NotAsked')
    })

    it('loading creates Loading variant', () => {
      const rd = loading()
      expect(rd.type).toBe('Loading')
    })

    it('success creates Success variant', () => {
      const rd = success(42)
      expect(rd.type).toBe('Success')
      expect(rd.data).toBe(42)
    })

    it('failure creates Failure variant', () => {
      const rd = failure('error')
      expect(rd.type).toBe('Failure')
      expect(rd.error).toBe('error')
    })
  })

  describe('type guards', () => {
    it('isNotAsked returns true for NotAsked', () => {
      expect(isNotAsked(notAsked())).toBe(true)
    })

    it('isLoading returns true for Loading', () => {
      expect(isLoading(loading())).toBe(true)
    })

    it('isSuccess returns true for Success', () => {
      expect(isSuccess(success(1))).toBe(true)
    })

    it('isFailure returns true for Failure', () => {
      expect(isFailure(failure('e'))).toBe(true)
    })
  })

  describe('map', () => {
    it('transforms Success data', () => {
      const result = map((x: number) => x * 2)(success(3))
      expect(isSuccess(result) && result.data).toBe(6)
    })

    it('preserves NotAsked', () => {
      const result = map((x: number) => x * 2)(notAsked<number, string>())
      expect(isNotAsked(result)).toBe(true)
    })

    it('preserves Loading', () => {
      const result = map((x: number) => x * 2)(loading<number, string>())
      expect(isLoading(result)).toBe(true)
    })

    it('preserves Failure', () => {
      const result = map((x: number) => x * 2)(failure<number, string>('error'))
      expect(isFailure(result) && result.error).toBe('error')
    })
  })

  describe('mapError', () => {
    it('transforms Failure error', () => {
      const result = mapError((e: string) => e.toUpperCase())(failure('error'))
      expect(isFailure(result) && result.error).toBe('ERROR')
    })

    it('preserves Success', () => {
      const result = mapError((e: string) => e.toUpperCase())(success<number, string>(42))
      expect(isSuccess(result) && result.data).toBe(42)
    })
  })

  describe('flatMap', () => {
    it('chains Success results', () => {
      const result = flatMap((x: number) => success(x * 2))(success(3))
      expect(isSuccess(result) && result.data).toBe(6)
    })

    it('short-circuits on Failure', () => {
      const result = flatMap((x: number) => success(x * 2))(failure<number, string>('error'))
      expect(isFailure(result) && result.error).toBe('error')
    })

    it('propagates inner Failure', () => {
      const result = flatMap((_: number) => failure<number, string>('inner'))(success(3))
      expect(isFailure(result) && result.error).toBe('inner')
    })
  })

  describe('fold', () => {
    it('calls onNotAsked for NotAsked', () => {
      const result = fold(
        () => 'not asked',
        () => 'loading',
        (x: number) => `success: ${x}`,
        (e: string) => `failure: ${e}`
      )(notAsked())
      expect(result).toBe('not asked')
    })

    it('calls onLoading for Loading', () => {
      const result = fold(
        () => 'not asked',
        () => 'loading',
        (x: number) => `success: ${x}`,
        (e: string) => `failure: ${e}`
      )(loading())
      expect(result).toBe('loading')
    })

    it('calls onSuccess for Success', () => {
      const result = fold(
        () => 'not asked',
        () => 'loading',
        (x: number) => `success: ${x}`,
        (e: string) => `failure: ${e}`
      )(success(42))
      expect(result).toBe('success: 42')
    })

    it('calls onFailure for Failure', () => {
      const result = fold(
        () => 'not asked',
        () => 'loading',
        (x: number) => `success: ${x}`,
        (e: string) => `failure: ${e}`
      )(failure('error'))
      expect(result).toBe('failure: error')
    })
  })

  describe('getOrElse', () => {
    it('returns data for Success', () => {
      expect(getOrElse(0)(success(42))).toBe(42)
    })

    it('returns default for NotAsked', () => {
      expect(getOrElse(0)(notAsked())).toBe(0)
    })

    it('returns default for Loading', () => {
      expect(getOrElse(0)(loading())).toBe(0)
    })

    it('returns default for Failure', () => {
      expect(getOrElse(0)(failure('error'))).toBe(0)
    })
  })

  describe('toMaybe', () => {
    it('returns Some for Success', () => {
      const maybe = toMaybe(success(42))
      expect(maybe.type).toBe('Some')
      expect(maybe.type === 'Some' && maybe.value).toBe(42)
    })

    it('returns Nothing for non-Success states', () => {
      expect(toMaybe(notAsked()).type).toBe('Nothing')
      expect(toMaybe(loading()).type).toBe('Nothing')
      expect(toMaybe(failure('e')).type).toBe('Nothing')
    })
  })
})
