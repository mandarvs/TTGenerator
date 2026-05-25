# Truck Telemetry Generator: Requriement Specifications and implementation Approach

## Objective

The truck telemetry generator generates synthetic truck telemetry data viz. GPS, IMU, J1939, and telematics device parameters for tens of thousands of trucks plying on the roads in India. It is used to test the scalablilty of Google CLoud Pubsub and Google Bigquery (BQ)  by ingesting the generated data into BQ via pubsub.

## Your role

Expert python programmer and expert in vehicle telemetry data formats.

## Signal Generation Specifications

### Signal Generation Details

The one signal should be generated every second for each running truck.

#### Signal attributes

##### Core identifiers

Each signal includes these core identifiers:

- event_ts :  time stamp of the signal in  ISO 8601  format, UTC time
- customer_id : ID of the customer owning the vehicle
- vehicle_id : Vehicle ID in format Vnnnnnnn i.e.g letter "V" followed by a 6 digit number
- device_id : Same as Vehicle ID with prefix "D" instead of letter "V"

##### GPS Signals

Each signal includes these GPS attributes :

- latitude
- longitude
- altitude_m : in meters
- gps_speed_kph : float, usually bwtween 0 and 100 mph
- heading_deg : float, between 0 and 360
- hdop : Always set to < 1.0 and < 0
- satellite_count : integer, always set to 12
- fix_quality : interger, varies between 0 and 2

##### IMU signals

Each signal includes these GPS attributes :

- accel_x_g : float, in gs, +-4g, micro gs also recorded
- accel_y_g : float, in gs, +-4g ,micro gs also recorded
- accel_z_g : float,in gs, +-4g , +-4g ,micro gs also recorded
- gyro_x_dps :float, in degrees per second +-200 deg per second is usual range
- gyro_y_dps :float, in degrees per second
- gyro_z_dps :float, in degrees per second

##### J1939 / vehicle bus signals

Each signal includes these GPS attributes :

- vehicle_speed_kph :float, starts at 0 and increases, keep changing as vehicle speed changes and comes doen to 0 as vehicle stops
- engine_rpm
- accelerator_pedal_pct :float, percentage value
- engine_load_pct: float, percentage value
- engine_torque_pct: float, percentage value
- fuel_rate_lph : float, between 1 to 3 lph
- total_fuel_used_l : in litres, starts at 0 and grows as fuel is consumed
- fuel_level_pct : float, percentage value. starts at 0.8 and reduces
- coolant_temp_c : in degrees centigrade, starts at 0 rapidly goes to 90 degrees and stabilizes
- oil_temp_c: in degrees centigrade, starts at 0 rapidly goes to 90 degrees and stabilizes
- oil_pressure_kpa :  float, in KPA goes from 100 at idle to 400 kPA
- intake_manifold_pressure_kpa: fixed at 140 kpa
- battery_voltage_v : fixed at 12 volts
- engine_hours : float, increases with drive time
- odometer_km : integer, increases as truck travels
- gear_selected : integer between 0 - 6 and reverse gear is -1; derived from current speed and behaviour (Loaded caps at 3, Empty climbs to 5 quickly, others use a default speed-band table)
- brake_switch : 1 byte , set to 0xFF  
- clutch_switch : integer set to 0
- pto_status : byte, set to 0
- active_dtc_count: integer, set to 0

##### Telematics device parameters

- ignition_status : integer, 0 for off , 1 for on
- external_power_v : float, in volts, fixed to 24
- backup_battery_v: float, in volts, fixed to 4
- device_temp_c: float, in degrees centigrade, fixed to 35
- gsm_signal_dbm : dBm, set to -50
- network_type : string, varies between : 2G, 3G, 4G, LTE
- gnss_fix_status : integer, 0 = No Fix; 1 = 2D Fix (Latitude/Longitude); 2 = 3D Fix (includes Altitude).
- can_bus_health : integer, fixed set to 0 = healthy
- storage_queue_depth : integer, fixed set to 100Number of telemetry records stored in internal memory waiting to be uploaded to the server.
- tamper_alert = integer, fixed set to 0


#### Truck attributes

##### Truck behaviour modelling

- Assigned source and destination location pair.

To keep things simple this location pair are picked from a set of preset location pairs. This set is static and prepopulated with locations in cities across india e.g. Pair 1 -  start_location:Dadar, start_city:Mumbai, start_latitude: < latitude value of dadar to 5 decimal digit accuracy>, start_longitude: < longitude value of dadar to 5 decimal digit accuracy>, end_location:  Andheri, end_city: Mumbai, end_latitude: < latitude value of andheri to 5 decimal digit accuracy>, end_longitude: < longitude value of  andheri to 5 decimal digit accuracy>.

- To keep things single the Truck travel in straight line, like the crow flies between source and destination locations.

Each truck is attached driving profile:

- Standard : Truck travels at max 50 kmph, at variable speed to the destination
- Fast: Truck travels at max 100 kmph, at constant speed to the destination
- Erratic : Truck drives at erratic speed and direction along the journey. The truck also reports wierd GPS locations as well as 0,0 as values to simulate broken GPS visibility, in which case relevant fix-quality value is also correctly reported
- Faulty : Truck stops half way
- Empty : Light truck, accelerates quickly to a 100 kmph top speed (~15 s) and upshifts through gears reaching gear 5 quickly
- Loaded : Heavy truck, accelerates slowly (~90 s) to a 50 kmph top speed and upshifts no higher than gear 3

Each truck starts at source latlong and sends first message with ignition_status = 1

At end of Trip or when the truck stops it send ignition_status = 0 message

## Implementation details

A generator will be a python command line application

Standard logging will be used to log debug and info level messages in the code at significant points

It will take command line parameters viz. number of trucks to generate signal for, vehicle id prefix strings e.g. "MH", "TN", "UP" etc. other command line parameters needed for "sinks"  

Object Oriented paradigms will be used to model the truck viz. "Truck" class will be generated which implements signal generation and behaviour modeling and store static telemetry data. It will maintain the internal driving status of the truck and implement nextSignal method to generate next signal. The signal will be a serialized viz, when choosing  comma separated string format, the payload will be serialzied in sequence of Core identifiers, GPS Signals, IMU signals, J1939 / vehicle bus signals and Telematics device parameters. Same applies for protobuf and JSON Seriazlizers

Values of the parameters for each truck will consistent within an instant viz. gps_speed_kph will always be equal to vehicle_speed_kph

"asyncio" python library and patterns will be used to benefit from mluti-core processors

A static list of source- destinations pairs will be created with around 80 entries 10 each for following cities: Delhi, Mumbai, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Jaipur. Each location will have statically assigned actual GPS location

A TruckFactory class will configure the number of trucks and assign them :

- Assign vehicle id, non duplicate IDs will be assigned
- Assign the truck the source-destination pair
- "Behaviour" values viz. Standard, Fast, Faulty, Empty, Loaded

A "signal generator driver" class will have start() method to call each trucks nextSignal method. The truck class will move the trucks location as per the behaviour and speed and generate and return the signal value.

Given the large number of truck values to be generated async pattern will be used to map and finally collect the signals and send to "sink" classes.

A "sink" class implemetation will be invoked by driver. The job of the sink class take a signal and forward it to storage layer. 2 sink classes will be implemented and invoked by the driver, viz. filesystem sync and pubsubsink.

filesystem sink will sequentially write the csv formatted file and pubsubsink will write to a pubsub topic.

3 payload serializers are needed, CSV, protobuf and json
