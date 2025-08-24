import random
import string
from typing import Set

# Keep track of active lobby names to avoid collisions
_active_lobby_names: Set[str] = set()

def generate_room_code(length: int = 6) -> str:
    """Generate a random alphanumeric room code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_player_id() -> str:
    """Generate a unique player ID."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def is_lobby_name_available(lobby_name: str) -> bool:
    """Check if a lobby name is available."""
    return lobby_name not in _active_lobby_names

def reserve_lobby_name(lobby_name: str) -> None:
    """Reserve a lobby name."""
    _active_lobby_names.add(lobby_name)

def release_lobby_name(lobby_name: str) -> None:
    """Release a lobby name."""
    _active_lobby_names.discard(lobby_name)

def validate_name(name: str) -> bool:
    """Validate player/lobby name."""
    if not name or len(name.strip()) == 0:
        return False
    if len(name) > 20:
        return False
    # Simple banned words check
    banned_words = ["admin", "host", "server", "bot"]
    return name.lower() not in banned_words
