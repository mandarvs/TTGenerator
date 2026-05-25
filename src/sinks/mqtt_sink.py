import aiomqtt
import paho.mqtt.client as paho
from src.sinks.base_sink import BaseSink
from src.models.payload import TelemetryPayload
from src.serializers.base_serializer import BaseSerializer

class MqttSink(BaseSink):
    def __init__(self, host: str, port: int, topic: str, serializer: BaseSerializer, metadata_fields: list[str] = None):
        super().__init__(serializer)
        self.host = host
        self.port = port
        self.topic = topic
        self.metadata_fields = metadata_fields or []
        self.client = None

    async def initialize(self):
        # aiomqtt prefers context manager usage, but we manually enter/exit
        # to fit the BaseSink initialize/close pattern.
        self.client = aiomqtt.Client(
            hostname=self.host,
            port=self.port,
            protocol=paho.MQTTv5
        )
        await self.client.__aenter__()

    async def write(self, payload: TelemetryPayload):
        data = self.serializer.serialize(payload)
        # If string, encode to bytes
        if isinstance(data, str):
            data = data.encode("utf-8")
        
        # Build MQTT v5 User Properties for metadata
        properties = paho.Properties(paho.PacketTypes.PUBLISH)
        user_props = []
        for field in self.metadata_fields:
            value = getattr(payload, field, None)
            if value is not None:
                # MQTT User Properties are (key, value) pairs of strings
                user_props.append((field, str(value)))
        
        if user_props:
            properties.UserProperty = user_props

        # Publish message
        await self.client.publish(self.topic, payload=data, properties=properties)
        
        self.total_processed += 1
        self.period_processed += 1

    async def close(self):
        if self.client:
            await self.client.__aexit__(None, None, None)
