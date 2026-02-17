import asyncio
import logging
from pyrogram.errors import FloodWait

class ParallelStreamer:
    def __init__(self, client, message, offset_bytes, limit_bytes, workers=15, prefetch_mb=50):
        """
        ULTRA-FAST MULTIPLEXING ENGINE
        workers: Number of simultaneous connections to Telegram DCs. (15 is incredibly fast).
        prefetch_mb: How many Megabytes to aggressively hold in RAM ahead of the user's download.
        """
        self.client = client
        self.message = message
        self.offset_bytes = offset_bytes
        self.limit_bytes = limit_bytes
        self.workers = workers
        self.chunk_size = 1024 * 1024  # 1MB Telegram Chunks
        self.prefetch_mb = prefetch_mb

    async def generate(self):
        start_chunk = self.offset_bytes // self.chunk_size
        end_chunk = self.limit_bytes // self.chunk_size
        
        # Bounded queue: Stops workers from downloading the end of the movie and crashing RAM
        queue = asyncio.Queue(maxsize=self.prefetch_mb)
        buffer = {}
        condition = asyncio.Condition()
        
        # Feeder: Puts the required chunks into the queue
        async def queue_feeder():
            try:
                for i in range(start_chunk, end_chunk + 1):
                    await queue.put(i)
            except asyncio.CancelledError:
                pass
        
        feeder_task = asyncio.create_task(queue_feeder())

        # Worker: Grabs a chunk from the queue and downloads it at max speed
        async def worker():
            while True:
                try:
                    chunk_index = await queue.get()
                except asyncio.CancelledError:
                    break
                
                retries = 0
                while retries < 5:
                    data = b""
                    try:
                        async for chunk in self.client.stream_media(self.message, offset=chunk_index, limit=1):
                            data += chunk
                        
                        # Save the downloaded chunk to RAM and alert the main thread
                        async with condition:
                            buffer[chunk_index] = data
                            condition.notify_all()
                        break  # Break out of retry loop on success
                        
                    except FloodWait as e:
                        logging.warning(f"⚠️ Telegram Rate Limit! Sleeping for {e.value}s")
                        await asyncio.sleep(e.value)
                    except Exception as e:
                        logging.error(f"Worker failed on chunk {chunk_index}, retrying... ({e})")
                        retries += 1
                        await asyncio.sleep(0.5)
                
                queue.task_done()

        # Spin up the massive parallel worker swarm
        worker_tasks = [asyncio.create_task(worker()) for _ in range(self.workers)]

        try:
            current_chunk = start_chunk
            bytes_to_send = self.limit_bytes - self.offset_bytes + 1
            first_part_cut = self.offset_bytes % self.chunk_size

            # The Main Thread: Feeds the perfectly ordered chunks to the user's browser/IDM
            while current_chunk <= end_chunk and bytes_to_send > 0:
                async with condition:
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
            # Absolute cleanup to prevent server memory leaks
            feeder_task.cancel()
            for t in worker_tasks:
                t.cancel()
            buffer.clear()
