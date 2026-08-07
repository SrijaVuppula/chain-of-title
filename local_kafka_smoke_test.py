"""
Local Kafka (Redpanda) smoke test for Chain of Title.
No account, no auth, no billing surface — just localhost:9092.
"""
import json, os, sys, time, uuid
from dotenv import load_dotenv
from confluent_kafka import Producer, Consumer, KafkaException

load_dotenv()
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.environ.get("KAFKA_TOPIC", "chain-of-title.decisions")

def produce_test_event():
    producer = Producer({"bootstrap.servers": BOOTSTRAP})
    test_id = str(uuid.uuid4())
    event = {
        "test_id": test_id,
        "shot_id": "SMOKE-TEST-001",
        "tool": "smoke-test",
        "status": "cleared",
        "reasoning": "Local connectivity smoke test, not a real decision.",
        "timestamp": time.time(),
    }
    result = {}
    def on_delivery(err, msg):
        if err is not None:
            result["error"] = err
        else:
            result["partition"], result["offset"] = msg.partition(), msg.offset()
    producer.produce(TOPIC, key=test_id, value=json.dumps(event), callback=on_delivery)
    producer.flush(timeout=10)
    if "error" in result:
        raise KafkaException(result["error"])
    print(f"Produced {test_id} -> partition {result['partition']}, offset {result['offset']}")
    return test_id

def consume_test_event(expected_test_id, timeout_seconds=15):
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": f"smoke-test-{uuid.uuid4()}",
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([TOPIC])
    deadline = time.time() + timeout_seconds
    found = False
    try:
        while time.time() < deadline:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())
            payload = json.loads(msg.value())
            if payload.get("test_id") == expected_test_id:
                print(f"Consumed matching event back: {payload}")
                found = True
                break
    finally:
        consumer.close()
    return found

def main():
    print(f"Testing {BOOTSTRAP} / topic '{TOPIC}'...")
    test_id = produce_test_event()
    if consume_test_event(test_id):
        print("\nSUCCESS: local Kafka pipeline is live.")
    else:
        print("\nFAILED: check the container is running (docker ps) and the topic name matches.")
        sys.exit(1)

if __name__ == "__main__":
    main()
