"""
fast.py — TurboStreamer (Render 512MB Safe Edition)
- Strictly caps RAM usage per connection to prevent OOM
- Detects IDM chunks and limits them to 1 worker
"""

import asyncio
import logging
import math
import os
from collections import OrderedDict
from typing import Optional
from pyrogram.errors import FloodWait

logger = logging.getLogger(__name__)

class TurboStreamer:
    def __init__(
        self,
        client,
        message,
        offset_bytes: int,
        limit_bytes: Optional[int],
        *,
        chunk_size: int = 1024 * 1024,
        max_workers: Optional[int] = None,
        batch_chunks: int = 2,           
        max_buffer_chunks: int = 10      
    ):
        self.client = client
        self.message = message
        self.offset_bytes = int(offset_bytes or 0)
        self.limit_bytes = None if limit_bytes is None else int(limit_bytes)
        self.chunk_size = int(chunk_size)
        self.batch_chunks = int(batch_chunks)
        self.max_buffer_chunks = int(max_buffer_chunks)
        self.max_retries = 5

        if self.limit_bytes is None:
            file_size = getattr(getattr(self.message, "document", None) or getattr(self.message, "video", None) or getattr(self.message, "audio", None), "file_size", None)
            if file_size:
                self.limit_bytes = int(file_size) - 1

        if self.limit_bytes is None:
            raise ValueError("limit_bytes (end) must be known or discoverable from message")

        self.req_length = self.limit_bytes - self.offset_bytes + 1
        if self.req_length < 0:
            raise ValueError("Invalid offset/limit combination")

        self.start_chunk = self.offset_bytes // self.chunk_size
        self.end_chunk = self.limit_bytes // self.chunk_size

        # 🔥 RENDER OOM PROTECTOR: Strict Worker Limits 🔥
        size_mb = max(1, self.req_length / (1024 * 1024))
        
        # If the requested size is < 50MB, it's IDM fetching a chunk. Give it 1 worker.
        if size_mb <= 50:
            self.workers = 1
        else:
            # If it's a huge browser download, give it max 3 workers to protect 512MB RAM
            self.workers = 3 

        # Hard cap the buffer to prevent memory spikes (Max ~10MB per connection)
        self.buffer_limit = min(self.max_buffer_chunks, 10)

    async def generate(self):
        total_chunks = self.end_chunk - self.start_chunk + 1
        
        batches = []
        i = self.start_chunk
        while i <= self.end_chunk:
            j = min(self.end_chunk, i + self.batch_chunks - 1)
            batches.append((i, j))
            i = j + 1

        queue = asyncio.Queue()
        for b in batches:
            queue.put_nowait(b)

        buffer = OrderedDict()
        got_event = asyncio.Condition()
        active = True
        sem = asyncio.Semaphore(self.workers)

        async def worker(worker_id: int):
            nonlocal active
            while active:
                try:
                    batch = await queue.get()
                except asyncio.CancelledError:
                    break
                if batch is None:
                    queue.task_done()
                    break
                    
                start_idx, end_idx = batch
                retries = 0
                
                while retries < self.max_retries:
                    try:
                        async with sem:
                            data_map = {}
                            async for piece in self.client.stream_media(self.message, offset=start_idx, limit=(end_idx - start_idx + 1)):
                                data_map.setdefault('acc', bytearray()).extend(piece)

                            acc = data_map.get('acc', bytearray())
                            cursor = 0
                            expected_chunks = end_idx - start_idx + 1
                            
                            for k in range(expected_chunks):
                                chunk_index = start_idx + k
                                start_pos = cursor
                                end_pos = min(cursor + self.chunk_size, len(acc))
                                chunk_bytes = bytes(acc[start_pos:end_pos])
                                cursor = end_pos
                                if chunk_bytes:
                                    data_map[chunk_index] = chunk_bytes
                                    
                            async with got_event:
                                for idx in range(start_idx, end_idx + 1):
                                    if idx in data_map:
                                        while len(buffer) >= self.buffer_limit:
                                            await got_event.wait()
                                        buffer[idx] = data_map[idx]
                                got_event.notify_all()
                        break
                    except FloodWait as fw:
                        wait_s = int(getattr(fw, "value", 1) or 1)
                        await asyncio.sleep(wait_s)
                        retries += 1
                    except asyncio.CancelledError:
                        break
                    except Exception as ex:
                        retries += 1
                        backoff = min(2 ** retries * 0.2, 5.0)
                        await asyncio.sleep(backoff)
                queue.task_done()

        worker_tasks = [asyncio.create_task(worker(i)) for i in range(self.workers)]

        try:
            current_chunk = self.start_chunk
            bytes_remaining = self.req_length
            first_part_cut = self.offset_bytes % self.chunk_size

            while current_chunk <= self.end_chunk and bytes_remaining > 0:
                async with got_event:
                    while current_chunk not in buffer:
                        if all(t.done() for t in worker_tasks) and queue.empty():
                            break
                        await got_event.wait()
                        
                    if current_chunk not in buffer:
                        break
                        
                    chunk_data = buffer.pop(current_chunk)
                    got_event.notify_all()

                if current_chunk == self.start_chunk and first_part_cut:
                    chunk_data = chunk_data[first_part_cut:]
                    first_part_cut = 0

                if len(chunk_data) > bytes_remaining:
                    chunk_data = chunk_data[:bytes_remaining]

                yield chunk_data
                bytes_remaining -= len(chunk_data)
                current_chunk += 1

        finally:
            for t in worker_tasks:
                if not t.done():
                    t.cancel()
            try:
                await asyncio.gather(*worker_tasks, return_exceptions=True)
            except Exception:
                pass
            buffer.clear()
