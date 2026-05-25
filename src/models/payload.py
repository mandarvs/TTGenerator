from dataclasses import dataclass
from datetime import datetime

@dataclass
class TelemetryPayload:
    """Represents a standard telematics data frame for a vehicle.

    This data container models a comprehensive set of vehicle diagnostics
    following J1939 SAE standards. It captures core identifiers, GPS coordinate
    snapshots, inertial measurement unit (IMU) readings, J1939 vehicle bus signals 
    (speeds, temperatures, fluid levels), and device hardware configurations.
    """
    # Core identifiers
    event_ts: str
    customer_id: str
    vehicle_id: str
    device_id: str

    # GPS Signals
    latitude: float
    longitude: float
    altitude_m: float
    gps_speed_kph: float
    heading_deg: float
    hdop: float
    satellite_count: int
    fix_quality: int

    # IMU signals
    accel_x_g: float
    accel_y_g: float
    accel_z_g: float
    gyro_x_dps: float
    gyro_y_dps: float
    gyro_z_dps: float

    # J1939 / vehicle bus signals
    vehicle_speed_kph: float
    engine_rpm: float
    accelerator_pedal_pct: float
    engine_load_pct: float
    engine_torque_pct: float
    fuel_rate_lph: float
    total_fuel_used_l: float
    fuel_level_pct: float
    coolant_temp_c: float
    oil_temp_c: float
    oil_pressure_kpa: float
    intake_manifold_pressure_kpa: float
    battery_voltage_v: float
    engine_hours: float
    odometer_km: int
    gear_selected: int
    brake_switch: int
    clutch_switch: int
    pto_status: int
    active_dtc_count: int

    # Telematics device parameters
    ignition_status: int
    external_power_v: float
    backup_battery_v: float
    device_temp_c: float
    gsm_signal_dbm: int
    network_type: str
    gnss_fix_status: int
    can_bus_health: int
    storage_queue_depth: int
    tamper_alert: int
