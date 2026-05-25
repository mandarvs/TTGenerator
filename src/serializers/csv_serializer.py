from src.serializers.base_serializer import BaseSerializer
from src.models.payload import TelemetryPayload

class CsvSerializer(BaseSerializer):
    @property
    def is_binary(self) -> bool:
        return False

    def serialize(self, payload: TelemetryPayload) -> str:
        fields = [
            payload.event_ts,
            payload.customer_id,
            payload.vehicle_id,
            payload.device_id,
            f"{payload.latitude:.5f}",
            f"{payload.longitude:.5f}",
            f"{payload.altitude_m:.1f}",
            f"{payload.gps_speed_kph:.2f}",
            f"{payload.heading_deg:.2f}",
            f"{payload.hdop:.1f}",
            str(payload.satellite_count),
            str(payload.fix_quality),
            f"{payload.accel_x_g:.2f}",
            f"{payload.accel_y_g:.2f}",
            f"{payload.accel_z_g:.2f}",
            f"{payload.gyro_x_dps:.1f}",
            f"{payload.gyro_y_dps:.1f}",
            f"{payload.gyro_z_dps:.1f}",
            f"{payload.vehicle_speed_kph:.2f}",
            f"{payload.engine_rpm:.0f}",
            f"{payload.accelerator_pedal_pct:.1f}",
            f"{payload.engine_load_pct:.1f}",
            f"{payload.engine_torque_pct:.1f}",
            f"{payload.fuel_rate_lph:.1f}",
            f"{payload.total_fuel_used_l:.2f}",
            f"{payload.fuel_level_pct:.2f}",
            f"{payload.coolant_temp_c:.1f}",
            f"{payload.oil_temp_c:.1f}",
            f"{payload.oil_pressure_kpa:.1f}",
            f"{payload.intake_manifold_pressure_kpa:.1f}",
            f"{payload.battery_voltage_v:.1f}",
            f"{payload.engine_hours:.4f}",
            str(payload.odometer_km),
            str(payload.gear_selected),
            f"0x{payload.brake_switch:02X}" if payload.brake_switch == 0xFF else str(payload.brake_switch),
            str(payload.clutch_switch),
            str(payload.pto_status),
            str(payload.active_dtc_count),
            str(payload.ignition_status),
            f"{payload.external_power_v:.1f}",
            f"{payload.backup_battery_v:.1f}",
            f"{payload.device_temp_c:.1f}",
            str(payload.gsm_signal_dbm),
            payload.network_type,
            str(payload.gnss_fix_status),
            str(payload.can_bus_health),
            str(payload.storage_queue_depth),
            str(payload.tamper_alert)
        ]
        return ",".join(fields)
