import { describe, it, expect } from 'vitest'
import {
  some,
  nothing,
  isSome,
  isNothing,
  map,
  flatMap,
  fold,
  getOrElse,
  getOrElseLazy,
  fromNullable,
  toNullable,
} from '../../src/algebraic/Maybe'

describe('Maybe', () => {
  describe('constructors', () => {
    it('some creates Some variant', () => {
      const maybe = some(42)
      expect(maybe.type).toBe('Some')
      expect(maybe.value).toBe(42)
    })

    it('nothing creates Nothing variant', () => {
      const maybe = nothing()
      expect(maybe.type).toBe('Nothing')
    })
  })

  describe('type guards', () => {
    it('isSome returns true for Some', () => {
      expect(isSome(some(1))).toBe(true)
    })

    it('isSome returns false for Nothing', () => {
      expect(isSome(nothing())).toBe(false)
    })

    it('isNothing returns true for Nothing', () => {
      expect(isNothing(nothing())).toBe(true)
    })

    it('isNothing returns false for Some', () => {
      expect(isNothing(some(1))).toBe(false)
    })
  })

  describe('map', () => {
    it('transforms Some value', () => {
      const result = map((x: number) => x * 2)(some(3))
      expect(isSome(result) && result.value).toBe(6)
    })

    it('preserves Nothing', () => {
      const result = map((x: number) => x * 2)(nothing<number>())
      expect(isNothing(result)).toBe(true)
    })
  })

  describe('flatMap', () => {
    it('chains Some results', () => {
      const result = flatMap((x: number) => some(x * 2))(some(3))
      expect(isSome(result) && result.value).toBe(6)
    })

    it('short-circuits on Nothing', () => {
      const result = flatMap((x: number) => some(x * 2))(nothing<number>())
      expect(isNothing(result)).toBe(true)
    })

    it('propagates inner Nothing', () => {
      const result = flatMap((_: number) => nothing<number>())(some(3))
      expect(isNothing(result)).toBe(true)
    })
  })

  describe('fold', () => {
    it('calls onSome for Some', () => {
      const result = fold(
        (x: number) => `value: ${x}`,
        () => 'nothing'
      )(some(42))
      expect(result).toBe('value: 42')
    })

    it('calls onNothing for Nothing', () => {
      const result = fold(
        (x: number) => `value: ${x}`,
        () => 'nothing'
      )(nothing<number>())
      expect(result).toBe('nothing')
    })
  })

  describe('getOrElse', () => {
    it('returns value for Some', () => {
      expect(getOrElse(0)(some(42))).toBe(42)
    })

    it('returns default for Nothing', () => {
      expect(getOrElse(0)(nothing())).toBe(0)
    })
  })

  describe('getOrElseLazy', () => {
    it('returns value for Some', () => {
      expect(getOrElseLazy(() => 0)(some(42))).toBe(42)
    })

    it('returns computed default for Nothing', () => {
      expect(getOrElseLazy(() => 100)(nothing())).toBe(100)
    })
  })

  describe('fromNullable', () => {
    it('creates Some for non-null value', () => {
      const result = fromNullable(42)
      expect(isSome(result) && result.value).toBe(42)
    })

    it('creates Nothing for null', () => {
      expect(isNothing(fromNullable(null))).toBe(true)
    })

    it('creates Nothing for undefined', () => {
      expect(isNothing(fromNullable(undefined))).toBe(true)
    })
  })

  describe('toNullable', () => {
    it('returns value for Some', () => {
      expect(toNullable(some(42))).toBe(42)
    })

    it('returns null for Nothing', () => {
      expect(toNullable(nothing())).toBeNull()
    })
  })
})
