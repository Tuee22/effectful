/**
 * RemoteDataRenderer component - Renders based on RemoteData state.
 */

import { ReactNode } from 'react'
import { RemoteData } from '../../algebraic/RemoteData'
import { Loading } from './Loading'
import { ErrorDisplay } from './ErrorDisplay'

interface RemoteDataRendererProps<T, E> {
  readonly data: RemoteData<T, E>
  readonly notAsked?: () => ReactNode
  readonly loading?: () => ReactNode
  readonly success: (data: T) => ReactNode
  readonly failure?: (error: E) => ReactNode
  readonly onRetry?: () => void
}

export function RemoteDataRenderer<T, E>({
  data,
  notAsked = () => null,
  loading = () => <Loading />,
  success,
  failure,
  onRetry,
}: RemoteDataRendererProps<T, E>) {
  switch (data.type) {
    case 'NotAsked':
      return <>{notAsked()}</>

    case 'Loading':
      return <>{loading()}</>

    case 'Success':
      return <>{success(data.data)}</>

    case 'Failure': {
      if (failure) {
        return <>{failure(data.error)}</>
      }

      const errorMessage =
        data.error && typeof data.error === 'object' && 'message' in data.error
          ? String((data.error as { message: unknown }).message)
          : String(data.error)

      return onRetry !== undefined
        ? <ErrorDisplay message={errorMessage} onRetry={onRetry} />
        : <ErrorDisplay message={errorMessage} />
    }
  }
}
