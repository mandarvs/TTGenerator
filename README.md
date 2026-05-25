# 🚛 TTGenerator: Realistic Truck Telemetry Simulator

TTGenerator is a high-performance, cooperative asynchronous Python utility designed to simulate real-time fleet movement and telematics. It generates comprehensive, SAE J1939-compliant telemetry snapshots and streams them concurrently to file systems, message brokers, and Google Cloud pipelines.

---

## 📐 System Architecture & Data Flow

Below is the end-to-end telemetry pipeline, from the real-time simulation engine down to downstream Bigtable and GCS Parquet storage:

```mermaid
graph TD
    A[main.py CLI] -->|Configures Fleet| B[TruckFactory]
    B -->|Instantiates| C[Active Truck Fleet]
    C -->|Cooperative ticks 1s| D[TelemetryDriver]
    D -->|Gathers events| E{Active Sinks}
    
    E -->|Write| F[FileSystemSink]
    E -->|Write| G[MqttSink]
    E -->|Write| H[KafkaSink]
    E -->|Write| I[PubSubSink]

    F -->|CSV/JSON/Proto| J[(Local Files)]
    G -->|Mqtt v5| K[mqtt_broker_stub.py]
    H -->|Kafka Events| L[Kafka Broker]
    I -->|GCP Pub/Sub Events| M[GCP Pub/Sub Topic]

    M -->|Stream Input| N[telemetry_to_bigtable.py]
    M -->|Stream Input| O[telemetry_to_parquet.py]

    N -->|Apache Beam Dataflow| P[(GCP Cloud Bigtable)]
    O -->|Apache Beam GCS Partitioning| Q[(GCP Cloud Storage Parquet)]
```

---

## 🌟 Core Features

- **Cooperative Asynchronous Multi-threading:** Powered by `asyncio`, simulating thousands of vehicles ticking at precise 1-second intervals.
- **Physical Vehicle Modeling:** Fully simulates throttle percentage, engine RPM, coolant/oil temperatures, transmission gear shifting, and fluid dynamics.
- **Realistic Route Progression:** Calculates geodetic compass bearings and travels along Great-Circle routes using the **Haversine formula**.
- **Flexible Behavior Presets:**
  - `Standard`: Consistent, rule-abiding driving.
  - `Fast`: High-speed, aggressive acceleration.
  - `Faulty`: Low velocities, breakdown simulation (stops halfway), and **intermittent GPS drift fault injection** (100–200km off-course).
  - `Empty` & `Loaded`: Mass adjustments that dynamically scale physical engine acceleration profiles.
- **Pluggable Architecture:** Support for multiple formats (CSV, JSON, Protobuf) and stream targets (MQTT, Apache Kafka, Google Cloud Pub/Sub, File System).

---

## 🛠️ Quick Start

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your system.

### 2. Installation
Clone the repository and navigate to the project directory:
```bash
git clone <your-repository-url>
cd TTGenerator
```

Create a virtual environment and install the required dependencies:
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/python    # On Linux/macOS
# or: .venv\Scripts\activate  # On Windows

# Install required packages
pip install -r requirements.txt
```

### 3. Run a Basic Simulation
Launch a quick 2-truck, 10-second simulation writing CSV outputs locally:
```bash
python main.py --count 2 --duration 10 --file telemetry_run.csv --file-format csv
```

---

## ☁️ GCP Pub/Sub Integration & Authentication Setup

To use the **Google Cloud Pub/Sub Sink**, you must have a GCP Project and a target Pub/Sub topic created and ready.

> [!IMPORTANT]
> **Prerequisites for Pub/Sub and Apache Beam Sinks:**
> 1. A Google Cloud Platform (GCP) project.
> 2. A Pub/Sub Topic (e.g. `telemetry-raw`).
> 3. Google Cloud SDK (`gcloud`) installed locally.

### Step 1: Install & Set Up the Google Cloud CLI
To authenticate with Google Cloud, you need the `gcloud` command-line tool.
* Detailed Installation Guide: [Google Cloud SDK Installation](https://cloud.google.com/sdk/docs/install)

Once installed, initialize your configuration and set your active project:
```bash
gcloud init
gcloud config set project <YOUR_GCP_PROJECT_ID>
```

### Step 2: Set Up Application Default Credentials (ADC)
This utility uses the official Google Cloud Python SDK which searches for credentials automatically via **Application Default Credentials**. 

Authenticate your local machine to use your user credentials for API calls:
```bash
gcloud auth application-default login
```
This command launches a browser window to authenticate with your GCP account and creates a local credential JSON file that the SDK automatically detects.

---

## 📋 CLI Parameters Reference

The primary driver is configured entirely through command-line arguments on `main.py`:

| Parameter | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `--count` | `int` | `10` | Number of active trucks to simulate in the fleet. |
| `--customer` | `str` | `CUST001` | Comma-separated customer IDs (assigns VINs round-robin). |
| `--prefix` | `str` | `V` | Prefix of the generated 17-character VIN. |
| `--duration` | `int` | `None` | Max duration (seconds) before starting a graceful shutdown. |
| `--file` | `str` | `None` | Output file path to write results locally. |
| `--file-format` | `str` | `csv` | Format for local file sink (`csv`, `json`, `proto`). |
| `--pubsub-project` | `str` | `None` | Target GCP Project ID for the Pub/Sub Sink. |
| `--pubsub-topic` | `str` | `None` | Target GCP Topic ID for the Pub/Sub Sink. |
| `--pubsub-format` | `str` | `proto` | Payload format for Pub/Sub (`csv`, `json`, `proto`). |
| `--mqtt-host` | `str` | `None` | MQTT broker host address. |
| `--mqtt-port` | `int` | `1883` | MQTT broker connection port. |
| `--mqtt-topic` | `str` | `None` | MQTT target topic name. |
| `--mqtt-format` | `str` | `json` | Payload format for MQTT (`csv`, `json`, `proto`). |
| `--behavior-dist` | `list` | `40 15 15 15 15` | Percentage distribution of presets (Standard, Fast, Faulty, Empty, Loaded). |
| `--start-time` | `str` | `None` | ISO 8601 string representing base clock starting timestamp. |

---

## 🔌 Running Auxiliary Components

### 1. Local MQTT v5 Broker Stub
For rapid testing of the MQTT sink without spinning up an enterprise Mosquitto broker, utilize the built-in, lightweight async MQTT v5 server stub:

```bash
# Start the broker stub (listens on 0.0.0.0:1883 by default)
python mqtt_broker_stub.py
```

Now, in a separate terminal, launch the simulator sending MQTT data locally:
```bash
python main.py --count 5 --mqtt-host localhost --mqtt-topic telemetry/trucks --mqtt-format json
```
Check `mqtt_stub.log` to watch incoming TCP publish packets.

### 2. Generate Lookup Master Data
Generate synthetic relational CSVs (customers, subscription tiers, vehicle metadata) to seed lookups in BigQuery:

```bash
python generate_master_data.py
```
Outputs `customer_master.csv`, `subscription_master.csv`, and `vehicle_master.csv`.

---

## ⚡ Running downstream Apache Beam Pipelines (Dataflow)

This utility includes two production-grade Apache Beam streaming pipelines in the root directory for ingestion.

> [!TIP]
> Make sure to install the supplementary requirements for Apache Beam before running these:
> ```bash
> pip install -r requirements.txt
> pip install -r parquet_requirements.txt
> ```

### A. Telemetry to Bigtable Streaming (`telemetry_to_bigtable.py`)
Reads telematics from Pub/Sub, parses column families (`gps`, `imu`, `vehicle`, `device`), and writes them to Google Cloud Bigtable.

```bash
python telemetry_to_bigtable.py \
  --input_subscription projects/<PROJECT>/subscriptions/<SUB_NAME> \
  --project_id <PROJECT_ID> \
  --instance_id <BIGTABLE_INSTANCE_ID> \
  --table_id <BIGTABLE_TABLE_ID> \
  --runner DirectRunner   # Use DirectRunner for local testing, or DataflowRunner for GCP
```

### B. Telemetry to Parquet GCS Archival (`telemetry_to_parquet.py`)
Reads telematics from Pub/Sub, dynamically windows messages, and writes Hive-partitioned Parquet files directly to Cloud Storage (`date=YYYY-MM-DD/vin=VXXXXXX/`).

```bash
python telemetry_to_parquet.py \
  --input_subscription projects/<PROJECT>/subscriptions/<SUB_NAME> \
  --output_path gs://<YOUR_BUCKET_NAME>/raw-telemetry/ \
  --project_id <PROJECT_ID> \
  --window_size 300 \
  --runner DirectRunner
```

---

## 🧬 Compiling the Telemetry Protocol Buffer

The simulator uses Google Protocol Buffers for fast, compact binary wire-transfers. If you edit the telematics schema defined in `src/models/telemetry.proto`, you must compile it to Python:

```bash
python -m grpc_tools.protoc \
  -I=src/models/ \
  --python_out=src/models/ \
  src/models/telemetry.proto
```
This updates the compiled classes in `src/models/telemetry_pb2.py`.
