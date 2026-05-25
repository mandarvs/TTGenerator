import json
import dataclasses
from src.serializers.base_serializer import BaseSerializer
from src.models.payload import TelemetryPayload

class JsonSerializer(BaseSerializer):
    @property
    def is_binary(self) -> bool:
        return False

    def serialize(self, payload: TelemetryPayload) -> str:
        # Convert the dataclass to a dictionary
        data_dict = dataclasses.asdict(payload)
        # Serialize the dictionary to a JSON string
        return json.dumps(data_dict)
