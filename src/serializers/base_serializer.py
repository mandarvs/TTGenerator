"""Abstract Base Class for all serialization strategies."""

from abc import ABC, abstractmethod
from src.models.payload import TelemetryPayload


class BaseSerializer(ABC):
    """Abstract interface that all data serializers must implement.

    Serializers transform the structured, strongly-typed TelemetryPayload objects
    into standard raw wire formats (e.g. CSV, JSON string, or Google Protobuf binary).
    """

    @abstractmethod
    def serialize(self, payload: TelemetryPayload):
        """Converts a TelemetryPayload object into its raw serialized representation.

        Args:
            payload (TelemetryPayload): The structured event data instance.

        Returns:
            Any: The serialized output (string or bytes).
        """
        pass

    @property
    @abstractmethod
    def is_binary(self) -> bool:
        """Indicates if the serialization output format is binary or text-based.

        Returns:
            bool: True if output is binary bytes, False if text-based.
        """
        pass
