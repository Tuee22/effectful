"""Unit tests for storage effects.

Tests verify that storage effects are frozen dataclasses with correct immutability,
equality, and hashing behavior.

Coverage: 100% of storage effects module.
"""

import pytest

from effectful.effects.storage import (
    DeleteObject,
    GetObject,
    ListObjects,
    PutObject,
)


class TestGetObject:
    """Tests for GetObject effect."""

    def test_get_object_is_frozen(self) -> None:
        """GetObject should be a frozen dataclass."""
        effect = GetObject(bucket="my-bucket", key="data/file.txt")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            setattr(effect, "bucket", "new-bucket")

    def test_get_object_attributes(self) -> None:
        """GetObject should store bucket and key."""
        effect = GetObject(bucket="my-bucket", key="data/file.txt")

        assert effect.bucket == "my-bucket"
        assert effect.key == "data/file.txt"

    def test_get_object_equality(self) -> None:
        """Equal GetObject instances should be equal."""
        effect1 = GetObject(bucket="my-bucket", key="data/file.txt")
        effect2 = GetObject(bucket="my-bucket", key="data/file.txt")

        assert effect1 == effect2

    def test_get_object_inequality(self) -> None:
        """Different GetObject instances should not be equal."""
        effect1 = GetObject(bucket="bucket1", key="file1.txt")
        effect2 = GetObject(bucket="bucket2", key="file2.txt")

        assert effect1 != effect2

    def test_get_object_hashable(self) -> None:
        """GetObject should be hashable (can be used in sets/dicts)."""
        effect1 = GetObject(bucket="my-bucket", key="data/file.txt")
        effect2 = GetObject(bucket="my-bucket", key="data/file.txt")

        # Can create set
        effect_set = {effect1, effect2}
        assert len(effect_set) == 1  # Same effect

        # Can use as dict key
        effect_dict = {effect1: "value"}
        assert effect_dict[effect2] == "value"


class TestPutObject:
    """Tests for PutObject effect."""

    def test_put_object_is_frozen(self) -> None:
        """PutObject should be a frozen dataclass."""
        effect = PutObject(bucket="my-bucket", key="data/file.txt", content=b"data")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            setattr(effect, "bucket", "new-bucket")

    def test_put_object_with_all_fields(self) -> None:
        """PutObject should accept all optional fields."""
        effect = PutObject(
            bucket="my-bucket",
            key="data/file.txt",
            content=b"test data",
            metadata={"uploaded-by": "user-123"},
            content_type="text/plain",
        )

        assert effect.bucket == "my-bucket"
        assert effect.key == "data/file.txt"
        assert effect.content == b"test data"
        assert effect.metadata == {"uploaded-by": "user-123"}
        assert effect.content_type == "text/plain"

    def test_put_object_minimal(self) -> None:
        """PutObject should work with just required fields."""
        effect = PutObject(bucket="my-bucket", key="file.txt", content=b"data")

        assert effect.bucket == "my-bucket"
        assert effect.key == "file.txt"
        assert effect.content == b"data"
        assert effect.metadata is None
        assert effect.content_type is None

    def test_put_object_defaults(self) -> None:
        """PutObject should have default None for metadata and content_type."""
        effect = PutObject(bucket="bucket", key="key", content=b"data")

        assert effect.metadata is None
        assert effect.content_type is None

    def test_put_object_equality(self) -> None:
        """Equal PutObject instances should be equal."""
        effect1 = PutObject(
            bucket="bucket",
            key="key",
            content=b"data",
            metadata={"key": "value"},
            content_type="text/plain",
        )
        effect2 = PutObject(
            bucket="bucket",
            key="key",
            content=b"data",
            metadata={"key": "value"},
            content_type="text/plain",
        )

        assert effect1 == effect2

    def test_put_object_inequality(self) -> None:
        """Different PutObject instances should not be equal."""
        effect1 = PutObject(bucket="bucket1", key="key1", content=b"data1")
        effect2 = PutObject(bucket="bucket2", key="key2", content=b"data2")

        assert effect1 != effect2

    def test_put_object_hashable(self) -> None:
        """PutObject should be hashable."""
        effect1 = PutObject(bucket="bucket", key="key", content=b"data")
        effect2 = PutObject(bucket="bucket", key="key", content=b"data")

        # Can create set
        effect_set = {effect1, effect2}
        assert len(effect_set) == 1  # Same effect

        # Can use as dict key
        effect_dict = {effect1: "value"}
        assert effect_dict[effect2] == "value"


class TestDeleteObject:
    """Tests for DeleteObject effect."""

    def test_delete_object_is_frozen(self) -> None:
        """DeleteObject should be a frozen dataclass."""
        effect = DeleteObject(bucket="my-bucket", key="file.txt")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            setattr(effect, "bucket", "new-bucket")

    def test_delete_object_attributes(self) -> None:
        """DeleteObject should store bucket and key."""
        effect = DeleteObject(bucket="my-bucket", key="data/file.txt")

        assert effect.bucket == "my-bucket"
        assert effect.key == "data/file.txt"

    def test_delete_object_equality(self) -> None:
        """Equal DeleteObject instances should be equal."""
        effect1 = DeleteObject(bucket="my-bucket", key="file.txt")
        effect2 = DeleteObject(bucket="my-bucket", key="file.txt")

        assert effect1 == effect2

    def test_delete_object_inequality(self) -> None:
        """Different DeleteObject instances should not be equal."""
        effect1 = DeleteObject(bucket="bucket1", key="file1.txt")
        effect2 = DeleteObject(bucket="bucket2", key="file2.txt")

        assert effect1 != effect2

    def test_delete_object_hashable(self) -> None:
        """DeleteObject should be hashable."""
        effect1 = DeleteObject(bucket="bucket", key="key")
        effect2 = DeleteObject(bucket="bucket", key="key")

        # Can create set
        effect_set = {effect1, effect2}
        assert len(effect_set) == 1

        # Can use as dict key
        effect_dict = {effect1: "value"}
        assert effect_dict[effect2] == "value"


class TestListObjects:
    """Tests for ListObjects effect."""

    def test_list_objects_is_frozen(self) -> None:
        """ListObjects should be a frozen dataclass."""
        effect = ListObjects(bucket="my-bucket")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            setattr(effect, "bucket", "new-bucket")

    def test_list_objects_with_prefix(self) -> None:
        """ListObjects should accept optional prefix."""
        effect = ListObjects(bucket="my-bucket", prefix="data/")

        assert effect.bucket == "my-bucket"
        assert effect.prefix == "data/"
        assert effect.max_keys == 1000  # Default

    def test_list_objects_with_max_keys(self) -> None:
        """ListObjects should accept custom max_keys."""
        effect = ListObjects(bucket="my-bucket", max_keys=100)

        assert effect.bucket == "my-bucket"
        assert effect.max_keys == 100
        assert effect.prefix is None  # Default

    def test_list_objects_defaults(self) -> None:
        """ListObjects should have default max_keys=1000, prefix=None."""
        effect = ListObjects(bucket="my-bucket")

        assert effect.bucket == "my-bucket"
        assert effect.prefix is None
        assert effect.max_keys == 1000

    def test_list_objects_all_parameters(self) -> None:
        """ListObjects should accept all parameters."""
        effect = ListObjects(bucket="my-bucket", prefix="reports/", max_keys=50)

        assert effect.bucket == "my-bucket"
        assert effect.prefix == "reports/"
        assert effect.max_keys == 50

    def test_list_objects_equality(self) -> None:
        """Equal ListObjects instances should be equal."""
        effect1 = ListObjects(bucket="bucket", prefix="data/", max_keys=100)
        effect2 = ListObjects(bucket="bucket", prefix="data/", max_keys=100)

        assert effect1 == effect2

    def test_list_objects_inequality(self) -> None:
        """Different ListObjects instances should not be equal."""
        effect1 = ListObjects(bucket="bucket1", prefix="data/")
        effect2 = ListObjects(bucket="bucket2", prefix="reports/")

        assert effect1 != effect2

    def test_list_objects_hashable(self) -> None:
        """ListObjects should be hashable."""
        effect1 = ListObjects(bucket="bucket", prefix="data/", max_keys=100)
        effect2 = ListObjects(bucket="bucket", prefix="data/", max_keys=100)

        # Can create set
        effect_set = {effect1, effect2}
        assert len(effect_set) == 1

        # Can use as dict key
        effect_dict = {effect1: "value"}
        assert effect_dict[effect2] == "value"
