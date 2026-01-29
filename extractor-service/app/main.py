from data.openf1_client import OpenF1Client
from utils.config import Config
# from utils.state_cache import StateCache
# from polling.leader_tracker import get_leader_lap_number
# from emitter.snapshot_builder import build_snapshot
from emitter.kafka_producer import KafkaProducerWrapper
import time

def main():
    client = OpenF1Client()
    producer = KafkaProducerWrapper()
    # cache = StateCache()
    iteration = 0

    while True:
        print(f"\n🕒 Polling from {client.timestamp_lower} to {client.timestamp_upper}")
        iteration += 1
        print("Polling OpenF1...iteration number: ", iteration)


        intervals = client.get_intervals()
        for i in intervals:
            producer.send("f1.intervals.raw", key=i["driver_number"], value=i)

        positions = client.get_positions()
        for p in positions:
            producer.send("f1.positions.raw", key=p["driver_number"], value=p)

        laps = client.get_laps()
        for l in laps:
            producer.send("f1.laps.raw", key=l["driver_number"], value=l)

        pit_data = client.get_pit_data()
        for pit in pit_data:
            producer.send("f1.pit.raw", key=pit["driver_number"], value=pit)

        race_events = client.get_race_control()
        for e in race_events:
            producer.send("f1.race_control.raw", key=client.session_key, value=e)
        

        client.advance()
        print(f"🔄 Advanced to {client.timestamp_lower} to {client.timestamp_upper}")
        producer.flush()
        time.sleep(Config.POLL_INTERVAL_SEC)

if __name__ == "__main__":
    main()
