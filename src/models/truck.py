"""Simulated truck physics and geographical movement model.

This module contains the Truck class, which represents an individual vehicle
in the simulated telemetry fleet. It simulates realistic GPS, J1939 engine bus,
and telematics hardware signals using Haversine navigation, acceleration models,
gear-shifting presets, fuel heuristics, and fault simulation profiles.
"""

import datetime
import random
import math
from src.models.location import Route
from src.models.payload import TelemetryPayload


class Truck:
    """Represents a simulated truck in the telemetry fleet.

    A Truck is instantiated with an active Route (start/end GPS locations) and a
    specific behavioral preset that dictates its physics parameters:
      - Standard: Solid acceleration, runs at standard speed limits (50 kph).
      - Fast: Aggressive acceleration, drives at high speeds (100 kph).
      - Faulty: Drives slowly, breaks down halfway, and experiences intermittent GPS drift.
      - Empty: Very fast acceleration (15s to top speed), matches Fast speeds.
      - Loaded: Slow acceleration (90s to top speed) due to weight, matches Standard speeds.
    """

    # Target velocities in km/h for the various behavioral presets
    TARGET_SPEED_KPH = {
        "Standard": 50.0,
        "Fast": 100.0,
        "Faulty": 30.0,
        "Empty": 100.0,
        "Loaded": 50.0,
    }

    # Time (in seconds) required to reach top target speed under linear acceleration
    ACCEL_TIME_S = {
        "Standard": 40,
        "Fast": 40,
        "Faulty": 40,
        "Empty": 15,
        "Loaded": 90,
    }

    # Gear shifting threshold configurations (min_speed_kph, gear_index)
    GEAR_BANDS = {
        "default": [(70, 5), (50, 4), (30, 3), (15, 2), (1, 1), (0, 0)],
        "Empty":   [(40, 5), (30, 4), (20, 3), (10, 2), (1, 1), (0, 0)],
        "Loaded":  [(30, 3), (15, 2), (1, 1), (0, 0)],
    }

    def __init__(
        self, 
        vehicle_id: str, 
        customer_id: str, 
        route: Route, 
        behavior: str, 
        batch_size: int = 1, 
        batch_duration: int = 1, 
        start_time: datetime.datetime = None
    ):
        """Initializes the Truck's physics state and geographical route parameters.

        Args:
            vehicle_id (str): Unique vehicle identifier (e.g. VIN).
            customer_id (str): Associated customer ID.
            route (Route): Start and End Location coordinates.
            behavior (str): Preset behavior ("Standard", "Fast", "Faulty", "Empty", "Loaded").
            batch_size (int, optional): Telemetry transmission batch threshold. Defaults to 1.
            batch_duration (int, optional): Maximum transmission latency threshold (seconds). Defaults to 1.
            start_time (datetime, optional): Base starting timestamp. Defaults to current UTC.
        """
        self.vehicle_id = vehicle_id
        self.device_id = f"D{vehicle_id[1:]}"
        self.customer_id = customer_id
        self.route = route
        self.behavior = behavior
        self.batch_size = batch_size
        self.batch_duration = batch_duration
        
        # Initial State
        self.current_lat = route.start.latitude
        self.current_lon = route.start.longitude
        self.ignition_status = 0  # Starts with engine/ignition off
        self._is_started = False
        self.event_ts = start_time or datetime.datetime.now(datetime.timezone.utc)
        
        # Physics / Trip State
        self.target_speed_kph = self._get_target_speed()
        self.speed_kph = 0.0  # Stationary initially
        self._acceleration_time = self.ACCEL_TIME_S.get(self.behavior, self.ACCEL_TIME_S["Standard"])
        self._acceleration_step = self.target_speed_kph / self._acceleration_time
        
        self.odometer_km = 0.0
        self.engine_hours = 0.0
        self.total_fuel_used_l = 0.0
        self.fuel_level_pct = 0.8  # Commences with 80% fuel level
        self.coolant_temp_c = 0.0  # Cold start
        self.oil_temp_c = 0.0
        self.is_finished = False

        # Batching state
        self._buffer = []
        self._time_since_last_report = 0
        
        # Geodetic calculations for direct bearings and total path distances
        self.bearing = self._calculate_bearing(
            route.start.latitude, route.start.longitude,
            route.end.latitude, route.end.longitude
        )
        self.total_trip_dist = self._calculate_distance(
            route.start.latitude, route.start.longitude,
            route.end.latitude, route.end.longitude
        )
        self.dist_traveled = 0.0

    def _get_target_speed(self) -> float:
        """Retrieves target top speed in kph based on truck's behavior profile."""
        return self.TARGET_SPEED_KPH.get(self.behavior, self.TARGET_SPEED_KPH["Standard"])

    def _get_gear(self) -> int:
        """Computes current transmission gear selection based on velocity bands.

        Returns:
            int: Selected gear index (0 for neutral/park).
        """
        if self.ignition_status == 0:
            return 0
        bands = self.GEAR_BANDS.get(self.behavior, self.GEAR_BANDS["default"])
        for min_speed, gear in bands:
            if self.speed_kph >= min_speed:
                return gear
        return 0

    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates the geodetic bearing from point 1 to point 2 in degrees.

        Args:
            lat1, lon1: Coordinates of Point 1.
            lat2, lon2: Coordinates of Point 2.

        Returns:
            float: Compass heading in degrees (0 - 360).
        """
        y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
            math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates the Great-Circle distance between two coordinates in kilometers.

        Employs the Haversine formula for geodetic curvature approximation:
            a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
            c = 2 * atan2(√a, √(1−a))
            d = R * c
        """
        R = 6371.0  # Earth's radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _calculate_random_offset_coords(self, lat: float, lon: float, distance_km: float) -> tuple[float, float]:
        """Calculates coordinates located at a random bearing and offset distance.

        Used strictly to simulate GPS noise/drift anomalies on "Faulty" trucks.
        """
        R = 6371.0
        bearing = math.radians(random.uniform(0, 360))
        
        lat1 = math.radians(lat)
        lon1 = math.radians(lon)

        lat2 = math.asin(math.sin(lat1) * math.cos(distance_km / R) +
                        math.cos(lat1) * math.sin(distance_km / R) * math.cos(bearing))
        
        lon2 = lon1 + math.atan2(math.sin(bearing) * math.sin(distance_km / R) * math.cos(lat1),
                                math.cos(distance_km / R) - math.sin(lat1) * math.sin(lat2))

        return math.degrees(lat2), math.degrees(lon2)

    def _update_state(self):
        """Ticks the physics, geographic position, and hardware telemetry by 1 second."""
        if self.is_finished:
            return

        # Advance internal clock by 1 second
        self.event_ts += datetime.timedelta(seconds=1)

        # Handle pre-start: first tick issues ignition OFF packet
        if not self._is_started:
            self._is_started = True
            self.ignition_status = 0 
            return

        # Turn ignition ON once driving commences
        self.ignition_status = 1

        # Gradually accelerate to target velocity
        if self.speed_kph < self.target_speed_kph and self.behavior != "Faulty":
            self.speed_kph = min(self.target_speed_kph, self.speed_kph + self._acceleration_step)
        
        # Simulates engine breakdown halfway through the journey for Faulty trucks
        if self.behavior == "Faulty" and self.dist_traveled >= (self.total_trip_dist / 2):
            self.speed_kph = 0
            self.ignition_status = 0
            self.is_finished = True
            return

        # Compute physical steps traveled during this second (velocity/3600.0)
        dist_step = self.speed_kph / 3600.0
        self.dist_traveled += dist_step
        self.odometer_km += dist_step
        self.engine_hours += 1/3600.0
        
        # Simple fuel consumption heuristics
        fuel_consumed = (self.speed_kph / 100.0) * 0.01
        self.total_fuel_used_l += fuel_consumed
        self.fuel_level_pct = max(0, self.fuel_level_pct - (fuel_consumed / 400.0))

        # Warm up engine fluids
        if self.coolant_temp_c < 90: self.coolant_temp_c += 0.5
        if self.oil_temp_c < 90: self.oil_temp_c += 0.4

        # Track progress and update geographical position
        if self.dist_traveled >= self.total_trip_dist:
            # Reached route terminus
            self.current_lat = self.route.end.latitude
            self.current_lon = self.route.end.longitude
            self.speed_kph = 0
            self.ignition_status = 0
            self.is_finished = True
        else:
            fraction = self.dist_traveled / self.total_trip_dist
            self.current_lat = self.route.start.latitude + (self.route.end.latitude - self.route.start.latitude) * fraction
            self.current_lon = self.route.start.longitude + (self.route.end.longitude - self.route.start.longitude) * fraction

        # Intermittent GPS drift fault injection for Faulty trucks (10% chance)
        if self.behavior == "Faulty" and not self.is_finished and random.random() < 0.1: 
            faulty_distance = random.uniform(100, 200)
            self.current_lat, self.current_lon = self._calculate_random_offset_coords(
                self.current_lat, self.current_lon, faulty_distance
            )

    def next_signal(self, force_flush: bool = False) -> list[TelemetryPayload]:
        """Ticks state forward and returns a batch of accumulated telemetry payload objects.

        Handles telemetry buffering and custom batch size/duration windows.

        Args:
            force_flush (bool, optional): Flushes the buffer immediately regardless of sizing. Defaults to False.

        Returns:
            list[TelemetryPayload]: List of TelemetryPayload events, or empty list if batch isn't complete.
        """
        self._update_state()
        
        # Ensure round accuracy on velocities
        current_speed = round(self.speed_kph, 2)
        
        payload = TelemetryPayload(
            # Core identifiers
            event_ts=self.event_ts.isoformat(),
            customer_id=self.customer_id,
            vehicle_id=self.vehicle_id,
            device_id=self.device_id,

            # GPS Signals
            latitude=round(self.current_lat, 5),
            longitude=round(self.current_lon, 5),
            altitude_m=50.0,
            gps_speed_kph=current_speed,
            heading_deg=round(self.bearing, 2),
            hdop=0.8,
            satellite_count=12,
            fix_quality=1,

            # IMU signals (Static for simplified representation)
            accel_x_g=0.01,
            accel_y_g=0.02,
            accel_z_g=0.98,
            gyro_x_dps=0.1,
            gyro_y_dps=0.1,
            gyro_z_dps=0.1,

            # J1939 / vehicle bus signals
            vehicle_speed_kph=current_speed,
            engine_rpm=round(self.speed_kph * 20, 0),
            accelerator_pedal_pct=20.0,
            engine_load_pct=25.0,
            engine_torque_pct=30.0,
            fuel_rate_lph=2.5,
            total_fuel_used_l=round(self.total_fuel_used_l, 2),
            fuel_level_pct=round(self.fuel_level_pct, 2),
            coolant_temp_c=round(self.coolant_temp_c, 1),
            oil_temp_c=round(self.oil_temp_c, 1),
            oil_pressure_kpa=300.0,
            intake_manifold_pressure_kpa=140.0,
            battery_voltage_v=12.0,
            engine_hours=round(self.engine_hours, 4),
            odometer_km=int(self.odometer_km),
            gear_selected=self._get_gear(),
            brake_switch=0xFF,
            clutch_switch=0,
            pto_status=0,
            active_dtc_count=0,

            # Telematics device parameters
            ignition_status=self.ignition_status,
            external_power_v=24.0,
            backup_battery_v=4.0,
            device_temp_c=35.0,
            gsm_signal_dbm=-50,
            network_type="4G",
            gnss_fix_status=2 if self.ignition_status else 0,
            can_bus_health=0,
            storage_queue_depth=100,
            tamper_alert=0
        )

        self._buffer.append(payload)
        self._time_since_last_report += 1

        if force_flush or len(self._buffer) >= self.batch_size or self._time_since_last_report >= self.batch_duration:
            batch = list(self._buffer)
            self._buffer.clear()
            self._time_since_last_report = 0
            return batch
        
        return []
