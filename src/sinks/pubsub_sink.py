from google.cloud import pubsub_v1
from src.sinks.base_sink import BaseSink
from src.models.payload import TelemetryPayload
from src.serializers.base_serializer import BaseSerializer
import asyncio

class PubSubSink(BaseSink):
    def __init__(self, project_id: str, topic_id: str, serializer: BaseSerializer, metadata_fields: list[str] = None):
        super().__init__(serializer)
        self.project_id = project_id
        self.topic_id = topic_id
        self.metadata_fields = metadata_fields or []
        # Batching settings for high throughput
        batch_settings = pubsub_v1.types.BatchSettings(
            max_bytes=1024 * 1024 * 5,  # 5 MB
            max_latency=0.5,            # 0.5 seconds
            max_messages=1000,          # 1000 messages
        )
        self.publisher = pubsub_v1.PublisherClient(batch_settings=batch_settings)
        self.topic_path = self.publisher.topic_path(project_id, topic_id)

    async def initialize(self):
        # Verify topic or other init logic if needed
        pass

    async def write(self, payload: TelemetryPayload):
        data = self.serializer.serialize(payload)
        # If string, encode to bytes
        if isinstance(data, str):
            data = data.encode("utf-8")
        
        # Extract metadata attributes from payload
        attributes = {}
        for field in self.metadata_fields:
            value = getattr(payload, field, None)
            if value is not None:
                attributes[field] = str(value)

        # Publisher.publish is non-blocking and returns a future
        self.publisher.publish(self.topic_path, data, **attributes)
        self.total_processed += 1
        self.period_processed += 1

    async def close(self):
        # No explicit close needed for publisher client, but typically 
        # you'd wait for futures if you wanted to guarantee delivery.
        pass
