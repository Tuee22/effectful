import { describe, it, expect } from 'vitest'
import {
  ok,
  err,
  isOk,
  isErr,
  map,
  mapErr,
  flatMap,
  fold,
  unwrapOr,
  unwrapOrElse,
  all,
} from '../../src/algebraic/Result'

describe('Result', () => {
  describe('constructors', () => {
    it('ok creates Ok variant', () => {
      const result = ok(42)
      expect(result.type).toBe('Ok')
      expect(result.value).toBe(42)
    })

    it('err creates Err variant', () => {
      const result = err('failure')
      expect(result.type).toBe('Err')
      expect(result.error).toBe('failure')
    })
  })

  describe('type guards', () => {
    it('isOk returns true for Ok', () => {
      expect(isOk(ok(1))).toBe(true)
    })

    it('isOk returns false for Err', () => {
      expect(isOk(err('e'))).toBe(false)
    })

    it('isErr returns true for Err', () => {
      expect(isErr(err('e'))).toBe(true)
    })

    it('isErr returns false for Ok', () => {
      expect(isErr(ok(1))).toBe(false)
    })
  })

  describe('map', () => {
    it('transforms Ok value', () => {
      const result = map((x: number) => x * 2)(ok(3))
      expect(isOk(result) && result.value).toBe(6)
    })

    it('preserves Err', () => {
      const result = map((x: number) => x * 2)(err('error'))
      expect(isErr(result) && result.error).toBe('error')
    })
  })

  describe('mapErr', () => {
    it('transforms Err error', () => {
      const result = mapErr((e: string) => e.toUpperCase())(err('error'))
      expect(isErr(result) && result.error).toBe('ERROR')
    })

    it('preserves Ok', () => {
      const result = mapErr((e: string) => e.toUpperCase())(ok(42))
      expect(isOk(result) && result.value).toBe(42)
    })
  })

  describe('flatMap', () => {
    it('chains Ok results', () => {
      const result = flatMap((x: number) => ok(x * 2))(ok(3))
      expect(isOk(result) && result.value).toBe(6)
    })

    it('short-circuits on Err', () => {
      const result = flatMap((x: number) => ok(x * 2))(err('error'))
      expect(isErr(result) && result.error).toBe('error')
    })

    it('propagates inner Err', () => {
      const result = flatMap((_: number) => err('inner error'))(ok(3))
      expect(isErr(result) && result.error).toBe('inner error')
    })
  })

  describe('fold', () => {
    it('calls onOk for Ok', () => {
      const result = fold(
        (x: number) => `value: ${x}`,
        (e: string) => `error: ${e}`
      )(ok(42))
      expect(result).toBe('value: 42')
    })

    it('calls onErr for Err', () => {
      const result = fold(
        (x: number) => `value: ${x}`,
        (e: string) => `error: ${e}`
      )(err('failure'))
      expect(result).toBe('error: failure')
    })
  })

  describe('unwrapOr', () => {
    it('returns value for Ok', () => {
      expect(unwrapOr(0)(ok(42))).toBe(42)
    })

    it('returns default for Err', () => {
      expect(unwrapOr(0)(err('error'))).toBe(0)
    })
  })

  describe('unwrapOrElse', () => {
    it('returns value for Ok', () => {
      expect(unwrapOrElse(() => 0)(ok(42))).toBe(42)
    })

    it('returns computed default for Err', () => {
      expect(unwrapOrElse((e: string) => e.length)(err('error'))).toBe(5)
    })
  })

  describe('all', () => {
    it('combines all Ok values', () => {
      const result = all([ok(1), ok(2), ok(3)])
      expect(isOk(result) && result.value).toEqual([1, 2, 3])
    })

    it('returns first Err', () => {
      const result = all([ok(1), err('error'), ok(3)])
      expect(isErr(result) && result.error).toBe('error')
    })

    it('handles empty array', () => {
      const result = all([])
      expect(isOk(result) && result.value).toEqual([])
    })
  })
})
