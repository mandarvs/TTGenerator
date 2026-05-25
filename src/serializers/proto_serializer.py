from src.serializers.base_serializer import BaseSerializer
from src.models.payload import TelemetryPayload
from src.models import telemetry_pb2

class ProtobufSerializer(BaseSerializer):
    @property
    def is_binary(self) -> bool:
        return True

    def serialize(self, payload: TelemetryPayload) -> bytes:
        signal = telemetry_pb2.TelemetrySignal()
        
        # Mapping payload to protobuf fields
        signal.event_ts = payload.event_ts
        signal.customer_id = payload.customer_id
        signal.vehicle_id = payload.vehicle_id
        signal.device_id = payload.device_id
        
        signal.latitude = payload.latitude
        signal.longitude = payload.longitude
        signal.altitude_m = payload.altitude_m
        signal.gps_speed_kph = payload.gps_speed_kph
        signal.heading_deg = payload.heading_deg
        signal.hdop = payload.hdop
        signal.satellite_count = payload.satellite_count
        signal.fix_quality = payload.fix_quality
        
        signal.accel_x_g = payload.accel_x_g
        signal.accel_y_g = payload.accel_y_g
        signal.accel_z_g = payload.accel_z_g
        signal.gyro_x_dps = payload.gyro_x_dps
        signal.gyro_y_dps = payload.gyro_y_dps
        signal.gyro_z_dps = payload.gyro_z_dps
        
        signal.vehicle_speed_kph = payload.vehicle_speed_kph
        signal.engine_rpm = payload.engine_rpm
        signal.accelerator_pedal_pct = payload.accelerator_pedal_pct
        signal.engine_load_pct = payload.engine_load_pct
        signal.engine_torque_pct = payload.engine_torque_pct
        signal.fuel_rate_lph = payload.fuel_rate_lph
        signal.total_fuel_used_l = payload.total_fuel_used_l
        signal.fuel_level_pct = payload.fuel_level_pct
        signal.coolant_temp_c = payload.coolant_temp_c
        signal.oil_temp_c = payload.oil_temp_c
        signal.oil_pressure_kpa = payload.oil_pressure_kpa
        signal.intake_manifold_pressure_kpa = payload.intake_manifold_pressure_kpa
        signal.battery_voltage_v = payload.battery_voltage_v
        signal.engine_hours = payload.engine_hours
        signal.odometer_km = payload.odometer_km
        signal.gear_selected = payload.gear_selected
        signal.brake_switch = payload.brake_switch
        signal.clutch_switch = payload.clutch_switch
        signal.pto_status = payload.pto_status
        signal.active_dtc_count = payload.active_dtc_count
        
        signal.ignition_status = payload.ignition_status
        signal.external_power_v = payload.external_power_v
        signal.backup_battery_v = payload.backup_battery_v
        signal.device_temp_c = payload.device_temp_c
        signal.gsm_signal_dbm = payload.gsm_signal_dbm
        signal.network_type = payload.network_type
        signal.gnss_fix_status = payload.gnss_fix_status
        signal.can_bus_health = payload.can_bus_health
        signal.storage_queue_depth = payload.storage_queue_depth
        signal.tamper_alert = payload.tamper_alert
        
        return signal.SerializeToString()
