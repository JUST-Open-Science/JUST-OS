from redis import Redis
import json

class ChatManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.message_ttl = 3600  # 1 hour in seconds

    def add_message(self, chat_id: str, message) -> None:
        key = f"chat:{chat_id}"

        # Add message to list
        self.redis.lpush(key, json.dumps(message))

        # Reset TTL on new message
        self.redis.expire(key, self.message_ttl)
        print("Added message")

    def get_history(self, chat_id: str):
        key = f"chat:{chat_id}"
        messages = self.redis.lrange(key, 0, -1)
        return [json.loads(msg) for msg in messages][::-1]