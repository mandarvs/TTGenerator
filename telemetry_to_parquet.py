import argparse
import json
import logging
from dateutil.parser import parse

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions
from apache_beam import window
from apache_beam.io import fileio
import pyarrow as pa
import pyarrow.parquet as pq

# Define the PyArrow schema for Parquet output
# Ensure types match the telemetry payload precisely
TELEMETRY_SCHEMA = pa.schema([
    ('event_ts', pa.string()),
    ('customer_id', pa.string()),
    ('vehicle_id', pa.string()),
    ('device_id', pa.string()),
    ('latitude', pa.float64()),
    ('longitude', pa.float64()),
    ('altitude_m', pa.float64()),
    ('gps_speed_kph', pa.float64()),
    ('heading_deg', pa.float64()),
    ('hdop', pa.float64()),
    ('satellite_count', pa.int64()),
    ('fix_quality', pa.int64()),
    ('accel_x_g', pa.float64()),
    ('accel_y_g', pa.float64()),
    ('accel_z_g', pa.float64()),
    ('gyro_x_dps', pa.float64()),
    ('gyro_y_dps', pa.float64()),
    ('gyro_z_dps', pa.float64()),
    ('vehicle_speed_kph', pa.float64()),
    ('engine_rpm', pa.float64()),
    ('accelerator_pedal_pct', pa.float64()),
    ('engine_load_pct', pa.float64()),
    ('engine_torque_pct', pa.float64()),
    ('fuel_rate_lph', pa.float64()),
    ('total_fuel_used_l', pa.float64()),
    ('fuel_level_pct', pa.float64()),
    ('coolant_temp_c', pa.float64()),
    ('oil_temp_c', pa.float64()),
    ('oil_pressure_kpa', pa.float64()),
    ('intake_manifold_pressure_kpa', pa.float64()),
    ('battery_voltage_v', pa.float64()),
    ('engine_hours', pa.float64()),
    ('odometer_km', pa.int64()),
    ('gear_selected', pa.int64()),
    ('brake_switch', pa.int64()),
    ('clutch_switch', pa.int64()),
    ('pto_status', pa.int64()),
    ('active_dtc_count', pa.int64()),
    ('ignition_status', pa.int64()),
    ('external_power_v', pa.float64()),
    ('backup_battery_v', pa.float64()),
    ('device_temp_c', pa.float64()),
    ('gsm_signal_dbm', pa.int64()),
    ('network_type', pa.string()),
    ('gnss_fix_status', pa.int64()),
    ('can_bus_health', pa.int64()),
    ('storage_queue_depth', pa.int64()),
    ('tamper_alert', pa.int64())
])

class CustomParquetSink(fileio.FileSink):
    """
    A custom FileSink that uses PyArrow to write Parquet files.
    This allows us to use fileio.WriteToFiles for dynamic routing/partitioning.
    """
    def __init__(self, schema):
        self._schema = schema
        self._writer = None

    def open(self, fh):
        # fh is the file-like object provided by Beam's filesystem layer
        self._writer = pq.ParquetWriter(fh, self._schema)

    def write(self, record):
        # Convert the dictionary record to a PyArrow Table
        table = pa.Table.from_pylist([record], schema=self._schema)
        self._writer.write_table(table)

    def flush(self):
        if self._writer:
            self._writer.close()
            self._writer = None

    def close(self):
        pass

class ParseAndTimestamp(beam.DoFn):
    def process(self, element):
        try:
            data = json.loads(element.decode('utf-8'))
            ts = parse(data['event_ts'])
            yield beam.window.TimestampedValue(data, ts.timestamp())
        except Exception as e:
            logging.error(f"Error parsing message: {e}")

def get_destination(element):
    """
    Constructs Hive-partitioned path: date=YYYY-MM-DD/vin=<VIN_NUMBER>
    """
    try:
        dt = parse(element['event_ts']).date()
        date_str = dt.strftime('%Y-%m-%d')
        vin = element.get('vehicle_id', 'unknown_vin')
        return f"date={date_str}/vin={vin}/"
    except Exception as e:
        logging.error(f"Error determining destination: {e}")
        return "date=unknown/vin=unknown"

def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_subscription', required=True, help='Pub/Sub subscription')
    parser.add_argument('--output_path', required=True, help='Base GCS path (gs://bucket/path/)')
    parser.add_argument('--project_id', required=True, help='GCP Project ID')
    parser.add_argument('--window_size', type=int, default=300, help='Window size (seconds)')
    
    known_args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(
        pipeline_args, 
        streaming=True, 
        project=known_args.project_id,
        save_main_session=True
    )
    
    with beam.Pipeline(options=pipeline_options) as p:
        (p 
         | "Read from PubSub" >> beam.io.ReadFromPubSub(subscription=known_args.input_subscription)
         | "Parse and Assign Timestamp" >> beam.ParDo(ParseAndTimestamp())
         | "Apply Window" >> beam.WindowInto(window.FixedWindows(known_args.window_size))
         | "Write Partitioned Parquet" >> fileio.WriteToFiles(
             path=known_args.output_path,
             # Pass a callable (lambda) to create the sink
             sink=lambda dest: CustomParquetSink(TELEMETRY_SCHEMA),
             destination=get_destination,
             file_naming=fileio.destination_prefix_naming(suffix='.parquet'),
             # Use 'shards' instead of 'num_shards' for this version of Beam
             shards=1 
         )
        )

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
