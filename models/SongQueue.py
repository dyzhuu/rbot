from collections import deque
from collections.abc import Sequence
from .Song import Song
import random

from typing import Deque, Tuple, Optional


class SongQueue:
    def __init__(self):
        self.queue: Deque[Song] = deque()

    def dequeue(self) -> Song:
        return self.queue.popleft()

    def enqueue(self, song: Song) -> None:
        self.queue.append(song)

    def enqueue_to_top(self, song: Song) -> None:
        self.queue.append(song)

    def extend(self, songs: Sequence[Song]) -> None:
        self.queue.extend(songs)

    def is_empty(self) -> bool:
        return len(self.queue) == 0

    def remove(self, index: int) -> None:
        del self.queue[index]

    def shuffle(self) -> None:
        random.shuffle(self.queue)

    def clear(self) -> None:
        self.queue.clear()

    def move_to_front(self, index) -> None:
        temp = self.queue[index]
        del self.queue[index]
        self.queue.appendleft(temp)

    def get_song_by_name(self, query: str) -> Tuple[int, Optional[Song]]:
        for index, song in enumerate(self.queue):
            if query.lower().replace(' ', '') in song.title.lower().replace(' ', ''):
                return index, song
        return -1, None

    def __len__(self):
        return len(self.queue)

    def __getitem__(self, index):
        return self.queue[index]
