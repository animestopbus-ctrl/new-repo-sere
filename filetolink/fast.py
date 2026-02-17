import asyncio
import logging

class ParallelStreamer:
    def __init__(self, client, message, offset_bytes, limit_bytes, workers=5):
        """
        Engineered to bypass Telegram's single-connection speed limit.
        workers=5 is safe for Render. Increase to 10 on a VPS for insane speeds.
        """
        self.client = client
        self.message = message
        self.offset_bytes = offset_bytes
        self.limit_bytes = limit_bytes
        self.workers = workers
        self.chunk_size = 1024 * 1024  # 1MB Chunks (Telegram Standard)

    async def generate(self):
        start_chunk = self.offset_bytes // self.chunk_size
        end_chunk = self.limit_bytes // self.chunk_size
        
        queue = asyncio.Queue()
        # Pre-load the queue with all the chunks we need to download
        for i in range(start_chunk, end_chunk + 1):
            queue.put_nowait(i)

        buffer = {}
        condition = asyncio.Condition()

        # The Worker that downloads chunks randomly from the queue
        async def worker():
            while not queue.empty():
                chunk_index = await queue.get()
                data = b""
                try:
                    # Ask Telegram for this specific 1MB piece
                    async for chunk in self.client.stream_media(self.message, offset=chunk_index, limit=1):
                        data += chunk
                    
                    # Save it to RAM and tell the main thread it's ready
                    async with condition:
                        buffer[chunk_index] = data
                        condition.notify_all()
                except Exception as e:
                    logging.error(f"Worker failed on chunk {chunk_index}, retrying...")
                    await asyncio.sleep(0.5)
                    await queue.put(chunk_index)  # Put back in line to retry
                finally:
                    queue.task_done()

        # Spin up the parallel workers
        tasks = [asyncio.create_task(worker()) for _ in range(self.workers)]

        try:
            current_chunk = start_chunk
            bytes_to_send = self.limit_bytes - self.offset_bytes + 1
            first_part_cut = self.offset_bytes % self.chunk_size

            # The Main Thread that streams bytes to the browser strictly in order
            while current_chunk <= end_chunk and bytes_to_send > 0:
                async with condition:
                    # Wait until the next specific chunk is downloaded by the workers
                    while current_chunk not in buffer:
                        await condition.wait()
                    
                    chunk_data = buffer.pop(current_chunk)
                
                # Trim the first chunk if the user skipped forward in the video
                if current_chunk == start_chunk and first_part_cut:
                    chunk_data = chunk_data[first_part_cut:]
                    first_part_cut = 0
                
                # Trim the last chunk to perfectly match the requested size
                if len(chunk_data) > bytes_to_send:
                    chunk_data = chunk_data[:bytes_to_send]

                yield chunk_data
                
                bytes_to_send -= len(chunk_data)
                current_chunk += 1
        finally:
            # Clean up memory and kill workers when download finishes or user cancels
            for t in tasks:
                t.cancel()
