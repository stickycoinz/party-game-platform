from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from app.schemas.lobby import Lobby
import asyncio
import time

class StorageBackend(ABC):
    """Abstract storage backend for lobby data."""
    
    @abstractmethod
    async def get_lobby(self, lobby_name: str) -> Optional[Lobby]:
        """Get lobby by name."""
        pass
    
    @abstractmethod
    async def set_lobby(self, lobby_name: str, lobby: Lobby) -> None:
        """Set/update lobby."""
        pass
    
    @abstractmethod
    async def delete_lobby(self, lobby_name: str) -> None:
        """Delete lobby."""
        pass
    
    @abstractmethod
    async def get_all_lobbies(self) -> Dict[str, Lobby]:
        """Get all active lobbies."""
        pass

class MemoryStorage(StorageBackend):
    """In-memory storage for development."""
    
    def __init__(self):
        self._lobbies: Dict[str, Lobby] = {}
        self._lobby_timestamps: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def get_lobby(self, lobby_name: str) -> Optional[Lobby]:
        async with self._lock:
            return self._lobbies.get(lobby_name)
    
    async def set_lobby(self, lobby_name: str, lobby: Lobby) -> None:
        async with self._lock:
            self._lobbies[lobby_name] = lobby
            self._lobby_timestamps[lobby_name] = time.time()
    
    async def delete_lobby(self, lobby_name: str) -> None:
        async with self._lock:
            self._lobbies.pop(lobby_name, None)
            self._lobby_timestamps.pop(lobby_name, None)
    
    async def get_all_lobbies(self) -> Dict[str, Lobby]:
        async with self._lock:
            return self._lobbies.copy()
    
    async def cleanup_old_lobbies(self, max_age_seconds: int = 3600) -> None:
        """Remove lobbies older than max_age_seconds."""
        current_time = time.time()
        async with self._lock:
            to_remove = [
                name for name, timestamp in self._lobby_timestamps.items()
                if current_time - timestamp > max_age_seconds
            ]
            for name in to_remove:
                self._lobbies.pop(name, None)
                self._lobby_timestamps.pop(name, None)

# Global storage instance
storage: StorageBackend = MemoryStorage()

async def get_storage() -> StorageBackend:
    """Get the current storage backend."""
    return storage
