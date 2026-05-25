"""Factory module for generating simulated truck fleets.

This module provides helper utilities for reading standard location mappings
from CSV, generating valid and unique ISO 3779 Vehicle Identification Numbers (VINs),
and a central TruckFactory class for spawning diverse, customer-assigned truck fleets
with configured behavioral distributions.
"""

import csv
import datetime
import hashlib
import random
from pathlib import Path
from src.models.location import Location, Route
from src.models.truck import Truck

_LOC_MASTER_PATH = Path(__file__).resolve().parents[2] / "loc_master.csv"

# ISO 3779 compliant alphabet for VIN numbers (excludes I, O, Q to prevent transcription errors)
VIN_ALPHABET = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"
VIN_LENGTH = 17
VIN_SERIAL_LENGTH = 6


def _load_locations(path: Path) -> list[Location]:
    """Loads location coordinates from the reference CSV master file.

    Args:
        path (Path): Path to the location master CSV file.

    Returns:
        list[Location]: List of parsed Location objects with name, city, latitude, and longitude.
    """
    with open(path, newline="") as f:
        return [
            Location(row["name"], row["city"], float(row["latitude"]), float(row["longitude"]))
            for row in csv.DictReader(f)
        ]


def _make_vin(prefix: str, customer_id: str, serial: int) -> str:
    """Generates a stable, reproducible ISO 3779 compliant Vehicle Identification Number (VIN).

    To ensure consistent VIN assignment across different runs of the generator, the
    internal middle character sequence is seeded deterministically using a SHA-256 hash 
    of the customer ID and vehicle serial number.

    Args:
        prefix (str): Prefix of the VIN (e.g. "V").
        customer_id (str): Customer identifier.
        serial (int): Customer-specific sequential serial number.

    Returns:
        str: A unique 17-character VIN.
    """
    prefix = prefix[: VIN_LENGTH - VIN_SERIAL_LENGTH]
    middle_len = VIN_LENGTH - VIN_SERIAL_LENGTH - len(prefix)
    # Seed local PRNG with SHA-256 of customer details to preserve global randomness state
    seed = int(hashlib.sha256(f"{customer_id}:{serial}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    middle = "".join(rng.choices(VIN_ALPHABET, k=middle_len))
    return f"{prefix}{middle}{str(serial).zfill(VIN_SERIAL_LENGTH)}"


class TruckFactory:
    """Central factory for instantiating and configuring simulated truck fleets.

    Exposes class-level routes and fleet generation logic that automatically models
    customer-to-VIN mapping and handles weighted truck behavior assignments (physics/fault profiles).
    """
    
    # Load default coordinates for Indian distribution routes
    LOCATIONS = _load_locations(_LOC_MASTER_PATH)

    # Preset profiles that dictate truck driving properties
    BEHAVIORS = ["Standard", "Fast", "Faulty", "Empty", "Loaded"]

    @classmethod
    def create_fleet(
        cls, 
        count: int, 
        vehicle_prefix: str, 
        customer_ids: list[str], 
        batch_size: int = 1, 
        batch_duration: int = 1, 
        behavior_dist: list[float] = None, 
        start_time: datetime.datetime = None
    ) -> list[Truck]:
        """Creates a fully configured fleet of simulated trucks.

        Distributes trucks across multiple customers and assigns random origin-destination
        pairs, initial parameters, and weighted behavior presets (standard, high speed, faulty, etc.).

        Args:
            count (int): Total number of trucks to simulate.
            vehicle_prefix (str): Character prefix for generated VINs.
            customer_ids (list[str]): List of active customer IDs.
            batch_size (int, optional): Message batching size for truck telemetry. Defaults to 1.
            batch_duration (int, optional): Maximum delay for batch reporting. Defaults to 1.
            behavior_dist (list[float], optional): Distribution percentages for the 5 presets. Defaults to None.
            start_time (datetime, optional): Simulation start timestamp. Defaults to current UTC.

        Returns:
            list[Truck]: List of spawned Truck instances ready to run.
        """
        fleet = []
        
        # Determine behavior weighting
        if count > 8:
            weights = behavior_dist or [40.0, 15.0, 15.0, 15.0, 15.0]
            total_weights = sum(weights)
            weights = [w / total_weights for w in weights]
        else:
            # Fallback for small fleet sizing
            weights = [0.40, 0.15, 0.15, 0.15, 0.15]

        n_customers = len(customer_ids)
        for i in range(count):
            # Round-robin customer assignment ensures reproducible VINs per-customer
            customer_id = customer_ids[i % n_customers]
            per_customer_serial = i // n_customers
            vehicle_id = _make_vin(vehicle_prefix, customer_id, per_customer_serial)

            # Randomly select a source and destination location for the route
            start, end = random.sample(cls.LOCATIONS, 2)
            route = Route(start, end)

            # Assign behavior profile based on specified weights
            behavior = random.choices(cls.BEHAVIORS, weights=weights)[0]

            fleet.append(
                Truck(
                    vehicle_id, 
                    customer_id, 
                    route, 
                    behavior, 
                    batch_size, 
                    batch_duration, 
                    start_time=start_time
                )
            )
        return fleet
