import asyncio
import struct
import datetime

# MQTT v5 Packet Types
CONNECT = 0x10
CONNACK = 0x20
PUBLISH = 0x30
PINGREQ = 0xC0
PINGRESP = 0xD0
DISCONNECT = 0xE0

def parse_varint(data):
    """Parses an MQTT variable-length integer."""
    multiplier = 1
    value = 0
    pos = 0
    while True:
        byte = data[pos]
        value += (byte & 127) * multiplier
        multiplier *= 128
        pos += 1
        if (byte & 128) == 0:
            break
    return value, pos

def parse_utf8(data):
    """Parses an MQTT UTF-8 encoded string (2 bytes length + content)."""
    length = struct.unpack("!H", data[:2])[0]
    return data[2:2+length].decode("utf-8"), 2+length

class MQTTStub:
    def __init__(self, host='0.0.0.0', port=1883, log_file='mqtt_stub.log'):
        self.host = host
        self.port = port
        self.log_file = log_file

    def log(self, message):
        timestamp = datetime.datetime.now().isoformat()
        with open(self.log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
        print(f"[{timestamp}] {message}")

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        self.log(f"New connection from {addr}")
        
        try:
            while True:
                header = await reader.read(1)
                if not header: break
                
                packet_type = header[0] >> 4
                
                # Read remaining length
                length_bytes = bytearray()
                while True:
                    b = await reader.read(1)
                    length_bytes.extend(b)
                    if (b[0] & 128) == 0: break
                
                remaining_length = parse_varint(length_bytes)[0]
                payload = await reader.read(remaining_length)

                if (header[0] & 0xF0) == CONNECT:
                    self.log("Received CONNECT (v5 assumed)")
                    # Send CONNACK: Fixed Header 0x20, Length 3, Flags 0, Reason 0, PropLength 0
                    writer.write(bytes([CONNACK, 0x03, 0x00, 0x00, 0x00]))
                    await writer.drain()
                    self.log("Sent CONNACK")

                elif (header[0] & 0xF0) == PUBLISH:
                    # Variable Header: Topic Name
                    topic, pos = parse_utf8(payload)
                    
                    # If QoS > 0, there would be a Packet ID here, but our sink defaults to QoS 0
                    
                    # MQTT v5 Properties
                    prop_len, var_pos = parse_varint(payload[pos:])
                    props_data = payload[pos+var_pos:pos+var_pos+prop_len]
                    
                    # Extract User Properties (ID 0x26)
                    metadata = []
                    p_pos = 0
                    while p_pos < len(props_data):
                        prop_id = props_data[p_pos]
                        p_pos += 1
                        if prop_id == 0x26: # User Property
                            key, k_len = parse_utf8(props_data[p_pos:])
                            p_pos += k_len
                            val, v_len = parse_utf8(props_data[p_pos:])
                            p_pos += v_len
                            metadata.append(f"{key}={val}")
                        else:
                            # Skip other properties (simplified for stub)
                            # Most v5 props are fixed length or UTF-8
                            break 

                    msg_payload = payload[pos+var_pos+prop_len:].decode('utf-8', errors='replace')
                    self.log(f"PUBLISH on '{topic}' | Metadata: {metadata} | Payload: {msg_payload[:100]}...")

                elif (header[0] & 0xF0) == PINGREQ:
                    writer.write(bytes([PINGRESP, 0x00]))
                    await writer.drain()

                elif (header[0] & 0xF0) == DISCONNECT:
                    self.log("Received DISCONNECT")
                    break

        except Exception as e:
            self.log(f"Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.log(f"Connection closed for {addr}")

    async def run(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        self.log(f"MQTT v5 Stub listening on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    stub = MQTTStub()
    try:
        asyncio.run(stub.run())
    except KeyboardInterrupt:
        pass
