"""Truck Telemetry Generator (TTGenerator) CLI Entrypoint.

This script instantiates the simulated fleet, binds them to target outputs
(sinks), and executes the asynchronous real-time simulation driver. It parses
arguments for customizing the simulation run (count, customer, duration, sinks,
and behavior distribution).

Examples:
    # Run simulation with 5 trucks and write to CSV file
    $ python main.py --count 5 --file telemetry.csv --file-format csv

    # Run simulation with 10 trucks, sending JSON payloads to an MQTT broker
    $ python main.py --count 10 --mqtt-host localhost --mqtt-topic telemetry/trucks --mqtt-format json

    # Run simulation sending protobuf-encoded payloads directly to GCP Cloud Pub/Sub
    $ python main.py --count 20 --pubsub-project my-gcp-project --pubsub-topic raw-telemetry
"""

import asyncio
import argparse
import datetime
import logging
import sys
import signal
from src.generator.factory import TruckFactory
from src.generator.driver import TelemetryDriver
from src.sinks.file_sink import FileSystemSink
from src.sinks.pubsub_sink import PubSubSink
from src.sinks.kafka_sink import KafkaSink
from src.sinks.mqtt_sink import MqttSink
from src.serializers.csv_serializer import CsvSerializer
from src.serializers.proto_serializer import ProtobufSerializer
from src.serializers.json_serializer import JsonSerializer

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

async def main():
    parser = argparse.ArgumentParser(description="Truck Telemetry Generator")
    parser.add_argument("--count", type=int, default=10, help="Number of trucks to simulate")
    parser.add_argument("--prefix", type=str, default="V", help="Vehicle ID prefix")
    parser.add_argument("--customer", type=str, default="CUST001", help="Customer ID")
    parser.add_argument("--file", type=str, help="Output file path")
    parser.add_argument("--file-format", type=str, choices=["csv", "proto", "json"], default="csv", help="Format for file output")
    parser.add_argument("--pubsub-project", type=str, help="GCP Project ID for PubSub")
    parser.add_argument("--pubsub-topic", type=str, help="GCP Topic ID for PubSub")
    parser.add_argument("--pubsub-format", type=str, choices=["csv", "proto", "json"], default="proto", help="Format for PubSub output")
    parser.add_argument("--duration", type=int, help="Optional duration in seconds to run the simulation before graceful shutdown.")
    parser.add_argument("--batch-size", type=int, default=1, help="Number of messages to aggregate before reporting.")
    parser.add_argument("--batch-duration", type=int, default=1, help="Maximum duration (seconds) before reporting aggregated messages.")
    parser.add_argument("--pubsub-metadata", type=str, nargs="+", default=["customer_id"], help="Payload fields to include as PubSub message attributes.")
    parser.add_argument("--kafka-bootstrap-servers", type=str, help="Kafka bootstrap servers (e.g., localhost:9092)")
    parser.add_argument("--kafka-topic", type=str, help="Kafka topic ID")
    parser.add_argument("--kafka-format", type=str, choices=["csv", "proto", "json"], default="json", help="Format for Kafka output")
    parser.add_argument("--kafka-metadata", type=str, nargs="+", default=["customer_id"], help="Payload fields to include as Kafka message headers.")
    parser.add_argument("--mqtt-host", type=str, help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--mqtt-topic", type=str, help="MQTT topic")
    parser.add_argument("--mqtt-format", type=str, choices=["csv", "proto", "json"], default="json", help="Format for MQTT output")
    parser.add_argument("--mqtt-metadata", type=str, nargs="+", default=["customer_id"], help="Payload fields to include as MQTT v5 User Properties.")
    parser.add_argument("--behavior-dist", type=float, nargs=5, default=[40.0, 15.0, 15.0, 15.0, 15.0], help="Distribution percentages for Standard, Fast, Faulty, Empty, and Loaded behaviors (e.g., 40 15 15 15 15). Sum must be 100.")
    parser.add_argument("--start-time", type=str, help="ISO 8601 timestamp to start generating signals from (e.g., 2026-05-11T09:00:00Z). Defaults to current UTC time. Naive timestamps are assumed UTC.")

    args = parser.parse_args()
    setup_logging()

    start_time = None
    if args.start_time:
        ts = args.start_time.replace("Z", "+00:00")
        start_time = datetime.datetime.fromisoformat(ts)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=datetime.timezone.utc)

    # 1. Create Sinks
    sinks = []
    if args.file:
        if args.file_format == "csv":
            serializer = CsvSerializer()
        elif args.file_format == "proto":
            serializer = ProtobufSerializer()
        else:
            serializer = JsonSerializer()
        sinks.append(FileSystemSink(args.file, serializer))
    if args.pubsub_project and args.pubsub_topic:
        if args.pubsub_format == "csv":
            serializer = CsvSerializer()
        elif args.pubsub_format == "proto":
            serializer = ProtobufSerializer()
        else:
            serializer = JsonSerializer()
        sinks.append(PubSubSink(args.pubsub_project, args.pubsub_topic, serializer, metadata_fields=args.pubsub_metadata))
    if args.kafka_bootstrap_servers and args.kafka_topic:
        if args.kafka_format == "csv":
            serializer = CsvSerializer()
        elif args.kafka_format == "proto":
            serializer = ProtobufSerializer()
        else:
            serializer = JsonSerializer()
        sinks.append(KafkaSink(args.kafka_bootstrap_servers, args.kafka_topic, serializer, metadata_fields=args.kafka_metadata))
    if args.mqtt_host and args.mqtt_topic:
        if args.mqtt_format == "csv":
            serializer = CsvSerializer()
        elif args.mqtt_format == "proto":
            serializer = ProtobufSerializer()
        else:
            serializer = JsonSerializer()
        sinks.append(MqttSink(args.mqtt_host, args.mqtt_port, args.mqtt_topic, serializer, metadata_fields=args.mqtt_metadata))

    if not sinks:
        print("Error: No sinks configured. Provide --file or --pubsub-project/--pubsub-topic.")
        sys.exit(1)

    # 2. Create Fleet
    customer_ids = [c.strip() for c in args.customer.split(',')]
    fleet = TruckFactory.create_fleet(args.count, args.prefix, customer_ids, args.batch_size, args.batch_duration, behavior_dist=args.behavior_dist, start_time=start_time)

    # 3. Start Driver
    driver = TelemetryDriver(fleet, sinks)

    # Register signal handlers for graceful shutdown
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, driver.request_shutdown)
    except NotImplementedError:
        # signal handlers are not supported on some platforms/configurations
        pass

    if args.duration:
        logging.getLogger(__name__).info(f"Scheduling graceful shutdown in {args.duration} seconds.")
        loop.call_later(args.duration, driver.request_shutdown)

    await driver.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
