"""
fast.py — TurboStreamer (upgraded)
- Adaptive worker count based on requested size & CPU
- Batch fetching (reduces pyrogram RPC overhead)
- Bounded in-memory buffer (prevents OOM)
- Ordered output guarantee
- FloodWait handling & exponential backoff
- Cancel-safe and cleans up worker tasks
"""

import asyncio
import logging
import math
import os
from collections import OrderedDict, deque
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
        chunk_size: int = 1024 * 1024,           # 1MB chunk
        max_workers: Optional[int] = None,       # if None auto-calc
        batch_chunks: int = 4,                   # fetch this many 1MB chunks per pyrogram call
        max_buffer_chunks: int = 64,             # max number of chunks to keep in memory window
        max_retries: int = 5
    ):
        """
        client: pyrogram client wrapper exposing stream_media(message, offset=chunk_index, limit=n_chunks)
        message: pyrogram message object
        offset_bytes: starting byte
        limit_bytes: last requested byte (inclusive) or None
        """
        self.client = client
        self.message = message
        self.offset_bytes = int(offset_bytes or 0)
        self.limit_bytes = None if limit_bytes is None else int(limit_bytes)
        self.chunk_size = int(chunk_size)
        self.batch_chunks = int(batch_chunks)
        self.max_buffer_chunks = int(max_buffer_chunks)
        self.max_retries = int(max_retries)

        if self.limit_bytes is None:
            # if unknown, attempt to use attribute from message.media
            file_size = getattr(getattr(self.message, "document", None) or getattr(self.message, "video", None) or getattr(self.message, "audio", None), "file_size", None)
            if file_size:
                self.limit_bytes = int(file_size) - 1

        if self.limit_bytes is None:
            raise ValueError("limit_bytes (end) must be known or discoverable from message")

        # computed fields
        self.req_length = self.limit_bytes - self.offset_bytes + 1
        if self.req_length < 0:
            raise ValueError("Invalid offset/limit combination")

        # determine start/end chunk indexes
        self.start_chunk = self.offset_bytes // self.chunk_size
        self.end_chunk = self.limit_bytes // self.chunk_size

        # adaptive workers calculation:
        cpu_count = max(1, (os.cpu_count() or 1))
        size_mb = max(1, self.req_length / (1024 * 1024))
        
        # base workers: 1 per ~50MB, but at least 1; cap by cpu_count*3
        suggested = min(max(1, math.ceil(size_mb / 50)), cpu_count * 3)
        if max_workers is None:
            self.workers = int(min(8, suggested))  # don't spawn too many by default
        else:
            self.workers = int(max(1, max_workers))

        # further tuning: if very large (500+ MB) allow more workers
        if size_mb >= 500:
            self.workers = min(12, max(self.workers, cpu_count * 4))

        # Limit buffer window to avoid memory spikes
        self.buffer_limit = max(8, min(self.max_buffer_chunks, self.max_buffer_chunks))

        logger.debug(
            "TurboStreamer init: req_length=%s bytes, chunk_size=%s, start_chunk=%s, end_chunk=%s, workers=%s, batch_chunks=%s",
            self.req_length, self.chunk_size, self.start_chunk, self.end_chunk, self.workers, self.batch_chunks
        )

    async def generate(self):
        """
        Async generator that yields ordered byte chunks ready for sending to client.
        """
        total_chunks = self.end_chunk - self.start_chunk + 1
        
        # Build batch ranges to reduce number of pyrogram RPCs:
        batches = []
        i = self.start_chunk
        while i <= self.end_chunk:
            j = min(self.end_chunk, i + self.batch_chunks - 1)
            batches.append((i, j))
            i = j + 1

        queue = asyncio.Queue()
        for b in batches:
            queue.put_nowait(b)

        # in-memory buffer: OrderedDict to preserve ascending chunk index order
        buffer = OrderedDict()
        got_event = asyncio.Condition()
        active = True

        # semaphore to limit number of simultaneous pyrogram stream_media calls (avoid flooding)
        sem = asyncio.Semaphore(self.workers * 2)

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
                
                # attempt to fetch this batch (multiple chunks in single call)
                while retries < self.max_retries:
                    try:
                        async with sem:
                            data_map = {}  # chunk_index -> bytes
                            # Use client's stream_media with offset=start_idx and limit=(end_idx-start_idx+1)
                            async for piece in self.client.stream_media(self.message, offset=start_idx, limit=(end_idx - start_idx + 1)):
                                # Accumulate into a running bytearray
                                data_map.setdefault('acc', bytearray()).extend(piece)

                            # Split acc into exactly chunk-sized blocks
                            acc = data_map.get('acc', bytearray())
                            cursor = 0
                            expected_chunks = end_idx - start_idx + 1
                            
                            for k in range(expected_chunks):
                                chunk_index = start_idx + k
                                start_pos = cursor
                                end_pos = min(cursor + self.chunk_size, len(acc))
                                chunk_bytes = bytes(acc[start_pos:end_pos])
                                cursor = end_pos
                                # store only if chunk_bytes non-empty
                                if chunk_bytes:
                                    data_map[chunk_index] = chunk_bytes
                                    
                            # Push to buffer cleanly
                            async with got_event:
                                for idx in range(start_idx, end_idx + 1):
                                    if idx in data_map:
                                        # if buffer window full, wait until consumer consumes some
                                        while len(buffer) >= self.buffer_limit:
                                            await got_event.wait()
                                        buffer[idx] = data_map[idx]
                                got_event.notify_all()
                        break
                    except FloodWait as fw:
                        wait_s = int(getattr(fw, "value", 1) or 1)
                        logger.warning("FloodWait(%s) in worker %s: sleeping %ss", wait_s, worker_id, wait_s)
                        await asyncio.sleep(wait_s)
                        retries += 1
                    except asyncio.CancelledError:
                        break
                    except Exception as ex:
                        retries += 1
                        backoff = min(2 ** retries * 0.2, 5.0)
                        logger.debug("Worker %s exception, retry %s: %s; backoff=%.2f", worker_id, retries, ex, backoff)
                        await asyncio.sleep(backoff)
                queue.task_done()

        # start workers
        worker_tasks = [asyncio.create_task(worker(i)) for i in range(self.workers)]

        try:
            # streaming consumer: yield chunks in order
            current_chunk = self.start_chunk
            bytes_remaining = self.req_length
            first_part_cut = self.offset_bytes % self.chunk_size

            while current_chunk <= self.end_chunk and bytes_remaining > 0:
                async with got_event:
                    while current_chunk not in buffer:
                        # if all workers finished and queue empty and chunk still not in buffer -> break
                        if all(t.done() for t in worker_tasks) and queue.empty():
                            break
                        await got_event.wait()
                        
                    if current_chunk not in buffer:
                        logger.debug("No more data available for chunk %s", current_chunk)
                        break
                        
                    chunk_data = buffer.pop(current_chunk)
                    got_event.notify_all() # notify producers that buffer freed some space

                if current_chunk == self.start_chunk and first_part_cut:
                    chunk_data = chunk_data[first_part_cut:]
                    first_part_cut = 0

                if len(chunk_data) > bytes_remaining:
                    chunk_data = chunk_data[:bytes_remaining]

                # yield the actual bytes to caller
                yield chunk_data

                bytes_remaining -= len(chunk_data)
                current_chunk += 1

        finally:
            # cleanup: cancel workers safely
            for t in worker_tasks:
                if not t.done():
                    t.cancel()
            try:
                await asyncio.gather(*worker_tasks, return_exceptions=True)
            except Exception:
                pass
            buffer.clear()
