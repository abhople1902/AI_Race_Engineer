import json
from confluent_kafka import Consumer
# from utils.config import Config

def main():
    consumer = Consumer({
        "bootstrap.servers": "kafka:9092",
        "group.id": "debug-consumer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })

    consumer.subscribe(["f1.race_control.raw"])
    print(" 🔍 Listening for race control messages...")

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                continue

            if msg.error():
                print(f"Error - {msg.error()}")
                continue

            event = json.loads(msg.value().decode("utf-8"))
            print(event)

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()

if __name__ == "__main__":
    main()