import argparse
import json
import logging
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions
from apache_beam.io.gcp.bigtableio import WriteToBigTable
from google.cloud.bigtable.row import DirectRow

class MapToBigtableRow(beam.DoFn):
    def __init__(self, project_id, instance_id, table_id):
        self.project_id = project_id
        self.instance_id = instance_id
        self.table_id = table_id

    def process(self, element):
        """
        Processes a PubsubMessage object.
        element.data: JSON payload bytes
        element.attributes: custom attributes (dict)
        element.message_id: Pub/Sub message ID
        """
        try:
            # Parse the payload
            payload_data = json.loads(element.data.decode('utf-8'))
            
            # Row Key: customer_id#vehicle_id#event_ts
            # Fallback to current time if event_ts is missing for some reason
            customer_id = payload_data.get('customer_id', 'unknown_customer')
            vehicle_id = payload_data.get('vehicle_id', 'unknown_vehicle')
            event_ts = payload_data.get('event_ts', 'unknown_ts')
            
            row_key = f"{customer_id}#{vehicle_id}#{event_ts}".encode('utf-8')
            row = DirectRow(row_key=row_key)
            
            # 1. Map Metadata
            # Write Pub/Sub system metadata
            if element.message_id:
                row.set_cell('metadata', b'pubsub_message_id', element.message_id.encode('utf-8'))
            
            # Write custom Pub/Sub attributes
            if element.attributes:
                for attr_key, attr_val in element.attributes.items():
                    col_name = f"attr_{attr_key}".encode('utf-8')
                    row.set_cell('metadata', col_name, str(attr_val).encode('utf-8'))

            # 2. Map Payload to families
            families = {
                'gps': [
                    'latitude', 'longitude', 'altitude_m', 'gps_speed_kph', 
                    'heading_deg', 'hdop', 'satellite_count', 'fix_quality'
                ],
                'imu': [
                    'accel_x_g', 'accel_y_g', 'accel_z_g', 
                    'gyro_x_dps', 'gyro_y_dps', 'gyro_z_dps'
                ],
                'vehicle': [
                    'vehicle_speed_kph', 'engine_rpm', 'accelerator_pedal_pct', 
                    'engine_load_pct', 'engine_torque_pct', 'fuel_rate_lph', 
                    'total_fuel_used_l', 'fuel_level_pct', 'coolant_temp_c', 
                    'oil_temp_c', 'oil_pressure_kpa', 'intake_manifold_pressure_kpa', 
                    'battery_voltage_v', 'engine_hours', 'odometer_km', 
                    'gear_selected', 'brake_switch', 'clutch_switch', 
                    'pto_status', 'active_dtc_count'
                ],
                'device': [
                    'ignition_status', 'external_power_v', 'backup_battery_v', 
                    'device_temp_c', 'gsm_signal_dbm', 'network_type', 
                    'gnss_fix_status', 'can_bus_health', 'storage_queue_depth', 
                    'tamper_alert', 'device_id'
                ]
            }

            for family, columns in families.items():
                for col in columns:
                    if col in payload_data and payload_data[col] is not None:
                        row.set_cell(
                            family, 
                            col.encode('utf-8'), 
                            str(payload_data[col]).encode('utf-8')
                        )
            
            # Also store raw IDs in device for easy access if needed
            row.set_cell('device', b'customer_id', str(customer_id).encode('utf-8'))
            row.set_cell('device', b'vehicle_id', str(vehicle_id).encode('utf-8'))
            row.set_cell('device', b'event_ts', str(event_ts).encode('utf-8'))

            return [row]
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            return []

def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_topic', help='Pub/Sub topic to read from (full path)')
    parser.add_argument('--input_subscription', help='Pub/Sub subscription to read from (full path)')
    parser.add_argument('--project_id', required=True, help='GCP Project ID')
    parser.add_argument('--instance_id', required=True, help='Bigtable Instance ID')
    parser.add_argument('--table_id', required=True, help='Bigtable Table ID')
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    if not (known_args.input_topic or known_args.input_subscription):
        parser.error("Either --input_topic or --input_subscription must be provided.")

    # We must enable streaming mode for Pub/Sub pipelines
    # We pass the project explicitly because DataflowRunner requires it
    pipeline_options = PipelineOptions(
        pipeline_args, 
        streaming=True, 
        project=known_args.project_id
    )
    pipeline_options.view_as(SetupOptions).save_main_session = True
    
    with beam.Pipeline(options=pipeline_options) as p:
        (p 
         | "Read from PubSub" >> beam.io.ReadFromPubSub(
             topic=known_args.input_topic,
             subscription=known_args.input_subscription,
             with_attributes=True) # Enables access to metadata attributes
         | "Decode and Map" >> beam.ParDo(MapToBigtableRow(
             known_args.project_id, 
             known_args.instance_id, 
             known_args.table_id))
         | "Write to Bigtable" >> WriteToBigTable(
             project_id=known_args.project_id,
             instance_id=known_args.instance_id,
             table_id=known_args.table_id)
        )

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
