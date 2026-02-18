import asyncio
import logging
from pyrogram.errors import FloodWait
logger = logging.getLogger(__name__)
class TurboStreamer:
    def __init__(self, client, message, offset_bytes, limit_bytes, workers=1):  # Changed default to 1 for Render free tier
        self.client = client
        self.message = message
        self.offset_bytes = offset_bytes
        self.limit_bytes = limit_bytes
        self.chunk_size = 1024 * 1024  # 1MB Chunks for perfect speed balancing
        self.workers = workers
        
        # Calculate start and end chunk indexes
        self.start_chunk = self.offset_bytes // self.chunk_size
        self.end_chunk = self.limit_bytes // self.chunk_size
        self.req_length = self.limit_bytes - self.offset_bytes + 1

    async def generate(self):
        # The Queue holds the chunk numbers we need to fetch
        queue = asyncio.Queue()
        for i in range(self.start_chunk, self.end_chunk + 1):
            await queue.put(i)  # Use await put for async safety
        
        # The Buffer holds the downloaded bytes: { chunk_index: b'data' }
        buffer = {}
        # The Condition notifies the main loop when a chunk arrives
        condition = asyncio.Condition()
        
        # Worker Flag to stop them if things go wrong
        active = True

        async def worker():
            nonlocal active
            while active:
                try:
                    # Get the next chunk index to fetch
                    chunk_index = await queue.get()
                except asyncio.CancelledError:
                    break
                
                retries = 0
                while retries < 5 and active:
                    try:
                        # Fetch exactly 1 chunk (1MB) from Telegram
                        chunk_data = b""
                        async for data in self.client.stream_media(
                            self.message,
                            offset=chunk_index,
                            limit=1
                        ):
                            chunk_data += data
                        
                        # Store in buffer and notify main loop
                        async with condition:
                            buffer[chunk_index] = chunk_data
                            condition.notify_all()
                        break  # Success!
                    
                    except FloodWait as e:
                        # If Telegram says "Wait 3s", we wait, then retry
                        await asyncio.sleep(e.value + 1)
                        retries += 1
                    except Exception as e:
                        # Unknown error? Wait 1s and retry
                        logger.warning(f"Worker Error on chunk {chunk_index}: {e}")
                        await asyncio.sleep(1)
                        retries += 1
                
                if retries >= 5:
                    # If we failed 5 times, we must stop the stream to prevent hanging
                    logger.error(f"Critical: Failed to fetch chunk {chunk_index} after 5 retries.")
                    active = False
                    async with condition:
                        condition.notify_all()  # Wake up main loop to crash safely
                
                queue.task_done()

        # 🔥 LAUNCH PARALLEL WORKERS 🔥
        tasks = [asyncio.create_task(worker()) for _ in range(self.workers)]
        
        current_chunk = self.start_chunk
        bytes_remaining = self.req_length
        first_part_cut = self.offset_bytes % self.chunk_size
        
        try:
            while current_chunk <= self.end_chunk and bytes_remaining > 0:
                async with condition:
                    # Wait until the CURRENT chunk is ready in the buffer
                    while current_chunk not in buffer and active:
                        await condition.wait()
                    
                    # If workers died and chunk is missing, stop stream
                    if not active and current_chunk not in buffer:
                        raise Exception("Stream workers died.")
                    
                    # Grab data and delete from RAM immediately
                    data = buffer.pop(current_chunk)
                
                # Slice the first chunk if the user requested a specific byte offset (Resume/Seek)
                if current_chunk == self.start_chunk and first_part_cut:
                    data = data[first_part_cut:]
                
                # Trim the last chunk if it's larger than needed
                if len(data) > bytes_remaining:
                    data = data[:bytes_remaining]
                
                yield data
                bytes_remaining -= len(data)
                current_chunk += 1
        
        finally:
            # Clean up: Kill workers and free RAM
            active = False
            for task in tasks:
                task.cancel()
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except:
                pass
            buffer.clear()
