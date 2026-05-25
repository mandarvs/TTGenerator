import asyncio
import logging
from src.sinks.base_sink import BaseSink
from src.models.truck import Truck

class TelemetryDriver:
    """Cooperative asynchronous driver for the telemetry simulation fleet.

    The TelemetryDriver is responsible for orchestrating the execution of the
    simulation, initializing registered sinks, ticking the simulation time steps
    concurrently across the fleet, collecting generated signals, and writing them to sinks.
    """

    def __init__(self, fleet: list[Truck], sinks: list[BaseSink]):
        """Initializes the TelemetryDriver.

        Args:
            fleet (list[Truck]): List of simulated Truck objects in the fleet.
            sinks (list[BaseSink]): List of data sinks to export telemetry to.
        """
        self.fleet = fleet
        self.sinks = sinks
        self.logger = logging.getLogger(__name__)
        self._shutdown_requested = False

    def request_shutdown(self):
        """Triggers a graceful shutdown of the simulation.
        
        Schedules a clean completion by ensuring final state changes are committed
        and all active trucks shut down their engines before sinks are closed.
        """
        self._shutdown_requested = True

    async def _send_final_signals(self):
        """Sends clean-up signals (e.g. ignition OFF) for all remaining active trucks."""
        self.logger.info("Sending final ignition OFF signals for active trucks...")
        active_trucks = [t for t in self.fleet if not t.is_finished]
        final_tasks = []
        for truck in active_trucks:
            truck.speed_kph = 0
            truck.ignition_status = 0
            truck.is_finished = True
            payloads = truck.next_signal(force_flush=True) 
            for payload in payloads:
                for sink in self.sinks:
                    final_tasks.append(sink.write(payload))
        
        if final_tasks:
            await asyncio.gather(*final_tasks)

    async def start(self):
        """Starts the real-time simulation loop.
        
        This method handles:
            1. Initializing all data export sinks.
            2. Continuously running the fleet simulation tick-by-tick (1-second intervals).
            3. Gathering generated telematics events concurrently.
            4. Writing and broadcasting events to registered sinks.
            5. Gracefully handling shutdowns or exceptions.
        """
        self.logger.info(f"Starting simulation for {len(self.fleet)} trucks.")
        
        # Initialize all sinks
        for sink in self.sinks:
            await sink.initialize()

        try:
            while not self._shutdown_requested and any(not t.is_finished for t in self.fleet):
                active_trucks = [t for t in self.fleet if not t.is_finished]
                
                # Generate signals for all active trucks concurrently
                batched_payloads = [t.next_signal() for t in active_trucks]
                
                # Flatten the list of lists
                all_payloads = [p for batch in batched_payloads for p in batch]
                
                # Send to all sinks
                sink_tasks = []
                for payload in all_payloads:
                    for sink in self.sinks:
                        sink_tasks.append(sink.write(payload))
                
                if sink_tasks:
                    await asyncio.gather(*sink_tasks)
                
                # Report stats for all sinks
                for sink in self.sinks:
                    sink.report_stats()
                
                await asyncio.sleep(1)
                
                if len(active_trucks) % 100 == 0:
                    self.logger.info(f"Active trucks: {len(active_trucks)}")
            
            if self._shutdown_requested:
                await self._send_final_signals()

        except Exception as e:
            self.logger.error(f"Simulation error: {e}")
        finally:
            self.logger.info("Closing sinks.")
            for sink in self.sinks:
                await sink.close()
