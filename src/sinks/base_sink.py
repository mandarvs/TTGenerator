"""Abstract Base Class defining the contract for all telemetry exporters (sinks)."""

import logging
from abc import ABC, abstractmethod
from src.models.payload import TelemetryPayload
from src.serializers.base_serializer import BaseSerializer


class BaseSink(ABC):
    """Abstract interface that all data export sinks must implement.

    Sinks handle the final dispatch of serialized telemetry payloads to external 
    systems, such as file systems, message brokers (Pub/Sub, Kafka, MQTT), 
    or databases.
    """

    def __init__(self, serializer: BaseSerializer):
        """Initializes the base sink with a concrete serializer.

        Args:
            serializer (BaseSerializer): The serializer instance (e.g. CSV, JSON, Proto)
                responsible for converting TelemetryPayload objects into raw bytes/strings.
        """
        self.serializer = serializer
        self.total_processed = 0
        self.period_processed = 0
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def initialize(self):
        """Asynchronously initializes the export sink.

        Used to establish TCP sockets, establish connections, authenticate, or 
        verify resource endpoints before simulation throughput begins.
        """
        pass
        
    @abstractmethod
    async def write(self, payload: TelemetryPayload):
        """Serializes and exports a TelemetryPayload event to the external receiver.

        Must be implemented as a non-blocking asynchronous operation.

        Args:
            payload (TelemetryPayload): The structured event data instance.
        """
        pass
        
    def report_stats(self):
        """Logs statistics regarding message processing rates and throughput totals."""
        self.logger.info(f"Processed {self.period_processed} messages in the last second (Total: {self.total_processed})")
        self.period_processed = 0

    @abstractmethod
    async def close(self):
        """Gracefully closes all external connections, file handlers, and streams."""
        pass
