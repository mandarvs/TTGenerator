import aiofiles
from src.sinks.base_sink import BaseSink
from src.models.payload import TelemetryPayload
from src.serializers.base_serializer import BaseSerializer
from src.serializers.csv_serializer import CsvSerializer

class FileSystemSink(BaseSink):
    def __init__(self, file_path: str, serializer: BaseSerializer):
        super().__init__(serializer)
        self.file_path = file_path
        self._file = None

    async def initialize(self):
        # Open in binary mode if using binary serializer, otherwise text
        mode = 'wb' if self.serializer.is_binary else 'w'
        self._file = await aiofiles.open(self.file_path, mode=mode)
        
        # Write Header ONLY for CSV
        if isinstance(self.serializer, CsvSerializer):
            header = "event_ts,customer_id,vehicle_id,device_id,latitude,longitude,altitude_m,gps_speed_kph,heading_deg,hdop,satellite_count,fix_quality,accel_x_g,accel_y_g,accel_z_g,gyro_x_dps,gyro_y_dps,gyro_z_dps,vehicle_speed_kph,engine_rpm,accelerator_pedal_pct,engine_load_pct,engine_torque_pct,fuel_rate_lph,total_fuel_used_l,fuel_level_pct,coolant_temp_c,oil_temp_c,oil_pressure_kpa,intake_manifold_pressure_kpa,battery_voltage_v,engine_hours,odometer_km,gear_selected,brake_switch,clutch_switch,pto_status,active_dtc_count,ignition_status,external_power_v,backup_battery_v,device_temp_c,gsm_signal_dbm,network_type,gnss_fix_status,can_bus_health,storage_queue_depth,tamper_alert"
            await self._file.write(header + "\n")

    async def write(self, payload: TelemetryPayload):
        if self._file:
            data = self.serializer.serialize(payload)
            if isinstance(data, str):
                await self._file.write(data + "\n")
            else:
                await self._file.write(data) # Binary data usually doesn't need newline
            await self._file.flush()
            self.total_processed += 1
            self.period_processed += 1

    async def close(self):
        if self._file:
            await self._file.close()
