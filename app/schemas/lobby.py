from pydantic import BaseModel
from typing import List, Optional
from app.schemas.game import GameData, GameState

class Player(BaseModel):
    name: str
    is_ready: bool
    player_id: Optional[str] = None

class Lobby(BaseModel):
    lobby_name: str
    host: str
    players: List[Player]
    game_state: GameState = GameState.WAITING
    current_game: Optional[GameData] = None
    host_token: Optional[str] = None

class LobbyCreate(BaseModel):
    lobby_name: str
    player_name: str

class LobbyJoin(BaseModel):
    lobby_name: str
    player_name: str

class LobbyInfo(BaseModel):
    """Public lobby information for discovery."""
    lobby_name: str
    player_count: int
    max_players: int = 12
    game_state: GameState
    current_game_type: Optional[str] = None
