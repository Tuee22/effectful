"""Unit tests for messaging effects.

Tests verify that messaging effects are frozen dataclasses with correct immutability,
equality, and hashing behavior.

Coverage: 100% of messaging effects module.
"""

import pytest

from effectful.domain.optional_value import Absent, Provided
from effectful.effects.messaging import (
    AcknowledgeMessage,
    ConsumeMessage,
    NegativeAcknowledge,
    PublishMessage,
)


class TestPublishMessage:
    """Tests for PublishMessage effect."""

    def test_publish_message_is_frozen(self) -> None:
        """PublishMessage should be a frozen dataclass."""
        effect = PublishMessage(topic="test-topic", payload=b"test data")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            setattr(effect, "topic", "new-topic")

    def test_publish_message_with_properties(self) -> None:
        """PublishMessage should accept optional properties."""
        effect = PublishMessage(
            topic="test-topic",
            payload=b"test data",
            properties={"key": "value"},
        )

        assert effect.topic == "test-topic"
        assert effect.payload == b"test data"
        assert effect.properties == Provided(value={"key": "value"})

    def test_publish_message_without_properties(self) -> None:
        """PublishMessage should work without properties (defaults to None)."""
        effect = PublishMessage(topic="test-topic", payload=b"test data")

        assert effect.topic == "test-topic"
        assert effect.payload == b"test data"
        assert effect.properties == Absent()

    def test_publish_message_equality(self) -> None:
        """Equal PublishMessage instances should be equal."""
        effect1 = PublishMessage(
            topic="test-topic",
            payload=b"test data",
            properties={"key": "value"},
        )
        effect2 = PublishMessage(
            topic="test-topic",
            payload=b"test data",
            properties={"key": "value"},
        )

        assert effect1 == effect2

    def test_publish_message_inequality(self) -> None:
        """Different PublishMessage instances should not be equal."""
        effect1 = PublishMessage(topic="topic1", payload=b"data1")
        effect2 = PublishMessage(topic="topic2", payload=b"data2")

        assert effect1 != effect2

    def test_publish_message_hashable(self) -> None:
        """PublishMessage should be hashable (can be used in sets/dicts)."""
        effect1 = PublishMessage(topic="test-topic", payload=b"test data")
        effect2 = PublishMessage(topic="test-topic", payload=b"test data")

        # Can create set
        effect_set = {effect1, effect2}
        assert len(effect_set) == 1  # Same effect

        # Can use as dict key
        effect_dict = {effect1: "value"}
        assert effect_dict[effect2] == "value"


class TestConsumeMessage:
    """Tests for ConsumeMessage effect."""

    def test_consume_message_is_frozen(self) -> None:
        """ConsumeMessage should be a frozen dataclass."""
        effect = ConsumeMessage(subscription="test-sub")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            setattr(effect, "subscription", "new-sub")

    def test_consume_message_with_custom_timeout(self) -> None:
        """ConsumeMessage should accept custom timeout."""
        effect = ConsumeMessage(subscription="test-sub", timeout_ms=10000)

        assert effect.subscription == "test-sub"
        assert effect.timeout_ms == 10000

    def test_consume_message_default_timeout(self) -> None:
        """ConsumeMessage should have default timeout of 5000ms."""
        effect = ConsumeMessage(subscription="test-sub")

        assert effect.subscription == "test-sub"
        assert effect.timeout_ms == 5000

    def test_consume_message_equality(self) -> None:
        """Equal ConsumeMessage instances should be equal."""
        effect1 = ConsumeMessage(subscription="test-sub", timeout_ms=1000)
        effect2 = ConsumeMessage(subscription="test-sub", timeout_ms=1000)

        assert effect1 == effect2

    def test_consume_message_hashable(self) -> None:
        """ConsumeMessage should be hashable."""
        effect = ConsumeMessage(subscription="test-sub", timeout_ms=1000)
        effect_set = {effect}
        assert len(effect_set) == 1


class TestAcknowledgeMessage:
    """Tests for AcknowledgeMessage effect."""

    def test_acknowledge_message_is_frozen(self) -> None:
        """AcknowledgeMessage should be a frozen dataclass."""
        effect = AcknowledgeMessage(message_id="msg-123")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            setattr(effect, "message_id", "msg-456")

    def test_acknowledge_message_attributes(self) -> None:
        """AcknowledgeMessage should store message_id."""
        effect = AcknowledgeMessage(message_id="msg-123")

        assert effect.message_id == "msg-123"

    def test_acknowledge_message_equality(self) -> None:
        """Equal AcknowledgeMessage instances should be equal."""
        effect1 = AcknowledgeMessage(message_id="msg-123")
        effect2 = AcknowledgeMessage(message_id="msg-123")

        assert effect1 == effect2

    def test_acknowledge_message_inequality(self) -> None:
        """Different AcknowledgeMessage instances should not be equal."""
        effect1 = AcknowledgeMessage(message_id="msg-123")
        effect2 = AcknowledgeMessage(message_id="msg-456")

        assert effect1 != effect2

    def test_acknowledge_message_hashable(self) -> None:
        """AcknowledgeMessage should be hashable."""
        effect = AcknowledgeMessage(message_id="msg-123")
        effect_set = {effect}
        assert len(effect_set) == 1


class TestNegativeAcknowledge:
    """Tests for NegativeAcknowledge effect."""

    def test_negative_acknowledge_is_frozen(self) -> None:
        """NegativeAcknowledge should be a frozen dataclass."""
        effect = NegativeAcknowledge(message_id="msg-123")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            setattr(effect, "message_id", "msg-456")

    def test_negative_acknowledge_with_delay(self) -> None:
        """NegativeAcknowledge should accept custom delay."""
        effect = NegativeAcknowledge(message_id="msg-123", delay_ms=5000)

        assert effect.message_id == "msg-123"
        assert effect.delay_ms == 5000

    def test_negative_acknowledge_default_delay(self) -> None:
        """NegativeAcknowledge should have default delay of 0ms."""
        effect = NegativeAcknowledge(message_id="msg-123")

        assert effect.message_id == "msg-123"
        assert effect.delay_ms == 0

    def test_negative_acknowledge_equality(self) -> None:
        """Equal NegativeAcknowledge instances should be equal."""
        effect1 = NegativeAcknowledge(message_id="msg-123", delay_ms=1000)
        effect2 = NegativeAcknowledge(message_id="msg-123", delay_ms=1000)

        assert effect1 == effect2

    def test_negative_acknowledge_hashable(self) -> None:
        """NegativeAcknowledge should be hashable."""
        effect = NegativeAcknowledge(message_id="msg-123", delay_ms=1000)
        effect_set = {effect}
        assert len(effect_set) == 1
