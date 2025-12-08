"""Integration tests for storage workflows with real MinIO S3.

This module tests storage effect workflows using run_ws_program
with real MinIO infrastructure. Each test uses clean_minio fixture
for declarative, idempotent test isolation.
"""

from collections.abc import Generator
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from effectful.adapters.s3_storage import S3ObjectStorage
from effectful.algebraic.result import Err, Ok
from effectful.domain.optional_value import Provided
from effectful.domain.s3_object import ObjectNotFound, PutSuccess, S3Object
from effectful.effects.storage import DeleteObject, GetObject, ListObjects, PutObject
from effectful.effects.websocket import SendText
from effectful.infrastructure.cache import ProfileCache
from effectful.infrastructure.repositories import ChatMessageRepository, UserRepository
from effectful.infrastructure.websocket import WebSocketConnection
from effectful.interpreters.composite import create_composite_interpreter
from effectful.programs.program_types import AllEffects, EffectResult
from effectful.programs.runners import run_ws_program


class TestStorageWorkflowIntegration:
    """Integration tests for storage workflows with real MinIO."""

    @pytest.mark.asyncio
    async def test_put_and_get_object_workflow(
        self, clean_minio: str, object_storage: S3ObjectStorage, mocker: MockerFixture
    ) -> None:
        """Workflow stores and retrieves object from real MinIO."""
        key = f"test/{uuid4()}/data.txt"
        content = b"Hello, World!"

        # Create interpreter with real storage
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            object_storage=object_storage,
        )

        # Define workflow
        def put_get_object_program(
            bucket: str, obj_key: str, data: bytes
        ) -> Generator[AllEffects, EffectResult, str]:
            # Put object
            put_result = yield PutObject(
                bucket=bucket,
                key=obj_key,
                content=data,
                content_type="text/plain",
            )

            match put_result:
                case PutSuccess(key=stored_key):
                    yield SendText(text=f"Stored: {stored_key}")
                case _:
                    yield SendText(text="Put failed")
                    return "put_failed"

            # Get object
            obj = yield GetObject(bucket=bucket, key=obj_key)

            match obj:
                case S3Object(content=retrieved_content):
                    yield SendText(text=f"Retrieved {len(retrieved_content)} bytes")
                    return "success"
                case ObjectNotFound():
                    yield SendText(text="Object not found")
                    return "not_found"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(
            put_get_object_program(clean_minio, key, content), interpreter
        )

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "success"
                assert mock_ws.send_text.call_count == 2
                mock_ws.send_text.assert_any_call(f"Stored: {key}")
                mock_ws.send_text.assert_any_call("Retrieved 13 bytes")
            case Err(error):
                pytest.fail(f"Expected Ok, got Err({error})")

    @pytest.mark.asyncio
    async def test_get_nonexistent_object_workflow(
        self, clean_minio: str, object_storage: S3ObjectStorage, mocker: MockerFixture
    ) -> None:
        """Workflow handles nonexistent object gracefully."""
        key = f"test/{uuid4()}/nonexistent.txt"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            object_storage=object_storage,
        )

        # Define workflow
        def get_nonexistent_program(
            bucket: str, obj_key: str
        ) -> Generator[AllEffects, EffectResult, str]:
            obj = yield GetObject(bucket=bucket, key=obj_key)

            match obj:
                case S3Object():
                    return "found"
                case ObjectNotFound():
                    yield SendText(text="Object not found")
                    return "not_found"
                case _:
                    return "error"

        # Act
        result = await run_ws_program(get_nonexistent_program(clean_minio, key), interpreter)

        # Assert
        match result:
            case Ok(outcome):
                assert outcome == "not_found"
                mock_ws.send_text.assert_called_once_with("Object not found")
            case Err(error):
                pytest.fail(f"Expected Ok('not_found'), got Err({error})")

    @pytest.mark.asyncio
    async def test_delete_object_workflow(
        self, clean_minio: str, object_storage: S3ObjectStorage, mocker: MockerFixture
    ) -> None:
        """Workflow deletes object from real MinIO."""
        key = f"test/{uuid4()}/to-delete.txt"

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            object_storage=object_storage,
        )

        # Define workflow
        def delete_object_program(
            bucket: str, obj_key: str
        ) -> Generator[AllEffects, EffectResult, bool]:
            # Put object first
            yield PutObject(bucket=bucket, key=obj_key, content=b"delete me")

            # Verify it exists
            obj1 = yield GetObject(bucket=bucket, key=obj_key)
            match obj1:
                case ObjectNotFound():
                    return False
                case S3Object():
                    pass
                case _:
                    return False

            # Delete it
            yield DeleteObject(bucket=bucket, key=obj_key)
            yield SendText(text="Object deleted")

            # Verify it's gone
            obj2 = yield GetObject(bucket=bucket, key=obj_key)
            return isinstance(obj2, ObjectNotFound)

        # Act
        result = await run_ws_program(delete_object_program(clean_minio, key), interpreter)

        # Assert
        match result:
            case Ok(deleted):
                assert deleted is True
                mock_ws.send_text.assert_called_once_with("Object deleted")
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")

    @pytest.mark.asyncio
    async def test_list_objects_workflow(
        self, clean_minio: str, object_storage: S3ObjectStorage, mocker: MockerFixture
    ) -> None:
        """Workflow lists objects in real MinIO."""
        prefix = f"list-test/{uuid4()}"
        keys = [f"{prefix}/file1.txt", f"{prefix}/file2.txt", f"{prefix}/file3.txt"]

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            object_storage=object_storage,
        )

        # Define workflow
        def list_objects_program(
            bucket: str, obj_keys: list[str], pfx: str
        ) -> Generator[AllEffects, EffectResult, int]:
            # Put multiple objects
            for key in obj_keys:
                yield PutObject(bucket=bucket, key=key, content=b"content")

            # List objects with prefix
            result = yield ListObjects(bucket=bucket, prefix=pfx)
            assert isinstance(result, list)

            yield SendText(text=f"Found {len(result)} objects")
            return len(result)

        # Act
        result = await run_ws_program(list_objects_program(clean_minio, keys, prefix), interpreter)

        # Assert
        match result:
            case Ok(count):
                assert count == 3
                mock_ws.send_text.assert_called_once_with("Found 3 objects")
            case Err(error):
                pytest.fail(f"Expected Ok(3), got Err({error})")

    @pytest.mark.asyncio
    async def test_file_upload_download_workflow(
        self, clean_minio: str, object_storage: S3ObjectStorage, mocker: MockerFixture
    ) -> None:
        """Workflow simulating file upload and download."""
        user_id = uuid4()
        filename = "document.pdf"
        key = f"uploads/{user_id}/{filename}"
        content = b"PDF content here..."
        metadata = {"user-id": str(user_id), "filename": filename}

        # Create interpreter
        mock_ws = mocker.AsyncMock(spec=WebSocketConnection)
        mock_ws.is_open.return_value = True
        mock_user_repo = mocker.AsyncMock(spec=UserRepository)
        mock_msg_repo = mocker.AsyncMock(spec=ChatMessageRepository)
        mock_cache = mocker.AsyncMock(spec=ProfileCache)

        interpreter = create_composite_interpreter(
            websocket_connection=mock_ws,
            user_repo=mock_user_repo,
            message_repo=mock_msg_repo,
            cache=mock_cache,
            object_storage=object_storage,
        )

        # Define workflow
        def upload_download_program(
            bucket: str,
            obj_key: str,
            data: bytes,
            meta: dict[str, str],
        ) -> Generator[AllEffects, EffectResult, bool]:
            # Upload file
            put_result = yield PutObject(
                bucket=bucket,
                key=obj_key,
                content=data,
                metadata=meta,
                content_type="application/pdf",
            )

            match put_result:
                case PutSuccess():
                    yield SendText(text="Upload complete")
                case _:
                    return False

            # Download file
            obj = yield GetObject(bucket=bucket, key=obj_key)

            match obj:
                case S3Object(content=retrieved, metadata=obj_meta, content_type=ct):
                    # Verify content
                    assert retrieved == data
                    assert obj_meta.get("user-id") == str(user_id)
                    assert ct == Provided(value="application/pdf")
                    yield SendText(text="Download complete")
                    return True
                case _:
                    return False

        # Act
        result = await run_ws_program(
            upload_download_program(clean_minio, key, content, metadata), interpreter
        )

        # Assert
        match result:
            case Ok(success):
                assert success is True
                assert mock_ws.send_text.call_count == 2
                mock_ws.send_text.assert_any_call("Upload complete")
                mock_ws.send_text.assert_any_call("Download complete")
            case Err(error):
                pytest.fail(f"Expected Ok(True), got Err({error})")
