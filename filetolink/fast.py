import asyncio
import logging
from pyrogram.errors import FloodWait

class TurboStreamer:
    def __init__(self, client, message, offset_bytes, limit_bytes):
        self.client = client
        self.message = message
        self.offset_bytes = offset_bytes
        self.limit_bytes = limit_bytes
        self.chunk_size = 1048576  # 1MB Telegram Chunk
        self.req_length = limit_bytes - offset_bytes + 1
        
        # 🔥 SMART ENGINE LOGIC 🔥
        # If requested size > 50MB (Standard Browser Download): Use 4 parallel workers to bypass 3MB/s limit.
        # If requested size < 50MB (IDM Chunk or Video Player Buffer): Use 1 worker to prevent server crashes.
        self.workers = 4 if self.req_length > (50 * 1024 * 1024) else 1

    async def generate(self):
        start_chunk = self.offset_bytes // self.chunk_size
        end_chunk = self.limit_bytes // self.chunk_size
        
        queue = asyncio.Queue()
        for i in range(start_chunk, end_chunk + 1):
            queue.put_nowait(i)
            
        buffer = {}
        condition = asyncio.Condition()
        
        async def worker():
            while not queue.empty():
                chunk_index = await queue.get()
                retries = 0
                while retries < 5:
                    try:
                        data = b""
                        # Request strictly 1 chunk directly from Telegram DC
                        async for chunk in self.client.stream_media(self.message, offset=chunk_index, limit=1):
                            data += chunk
                            
                        async with condition:
                            buffer[chunk_index] = data
                            condition.notify_all()
                        break
                    except FloodWait as e:
                        logging.warning(f"Telegram Throttle: Sleeping {e.value}s")
                        await asyncio.sleep(e.value)
                    except Exception as e:
                        retries += 1
                        await asyncio.sleep(0.5)
                queue.task_done()

        # Spin up the Turbo Workers
        worker_tasks = [asyncio.create_task(worker()) for _ in range(self.workers)]
        
        try:
            current_chunk = start_chunk
            bytes_to_send = self.req_length
            first_part_cut = self.offset_bytes % self.chunk_size

            while current_chunk <= end_chunk and bytes_to_send > 0:
                async with condition:
                    # Wait exactly for the next required chunk to ensure smooth playback/download
                    while current_chunk not in buffer:
                        await condition.wait()
                    chunk_data = buffer.pop(current_chunk)

                if current_chunk == start_chunk and first_part_cut:
                    chunk_data = chunk_data[first_part_cut:]
                    first_part_cut = 0

                if len(chunk_data) > bytes_to_send:
                    chunk_data = chunk_data[:bytes_to_send]

                yield chunk_data
                
                bytes_to_send -= len(chunk_data)
                current_chunk += 1
        finally:
            for t in worker_tasks:
                t.cancel()
            buffer.clear()
