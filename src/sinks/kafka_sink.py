from confluent_kafka import Producer
from src.sinks.base_sink import BaseSink
from src.models.payload import TelemetryPayload
from src.serializers.base_serializer import BaseSerializer

class KafkaSink(BaseSink):
    def __init__(self, bootstrap_servers: str, topic: str, serializer: BaseSerializer, metadata_fields: list[str] = None):
        super().__init__(serializer)
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.metadata_fields = metadata_fields or []
        
        # Initialize Kafka Producer
        conf = {
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': 'ttgenerator',
            'linger.ms': 10,
            'batch.num.messages': 1000
        }
        self.producer = Producer(conf)

    async def initialize(self):
        # Optional: Check cluster connectivity
        pass

    async def write(self, payload: TelemetryPayload):
        data = self.serializer.serialize(payload)
        # If string, encode to bytes
        if isinstance(data, str):
            data = data.encode("utf-8")
        
        # Extract metadata attributes from payload as Kafka headers
        # Kafka headers require a list of tuples: [(key, value_bytes), ...]
        headers = []
        for field in self.metadata_fields:
            value = getattr(payload, field, None)
            if value is not None:
                headers.append((field, str(value).encode('utf-8')))

        # Produce message
        self.producer.produce(self.topic, value=data, headers=headers)
        
        # Poll to handle internal callbacks (non-blocking)
        self.producer.poll(0)
        
        self.total_processed += 1
        self.period_processed += 1

    async def close(self):
        if self.producer:
            self.logger.info(f"Flushing remaining Kafka messages for topic {self.topic}...")
            self.producer.flush()
