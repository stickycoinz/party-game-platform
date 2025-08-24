from pydantic import BaseModel
from typing import Dict, List, Optional, Literal, Any, Union
from enum import Enum

# Game State Enums
class GameType(str, Enum):
    TAP_GAUNTLET = "tap_gauntlet"
    BUZZER_TRIVIA = "buzzer_trivia"
    IMPOSTOR_PROMPT = "impostor_prompt"
    SHOTGUN_ROULETTE = "shotgun_roulette"

class GameState(str, Enum):
    WAITING = "waiting"
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"

# Player Score Model
class PlayerScore(BaseModel):
    player_name: str
    score: int
    position: int

# Game Results
class GameResults(BaseModel):
    game_type: GameType
    winner: Optional[str] = None
    scores: List[PlayerScore]
    duration_seconds: float

# Base Game Data
class BaseGameData(BaseModel):
    game_type: GameType
    state: GameState
    start_time: Optional[float] = None
    end_time: Optional[float] = None

# Tap Gauntlet specific data
class TapGauntletData(BaseGameData):
    game_type: Literal[GameType.TAP_GAUNTLET] = GameType.TAP_GAUNTLET
    duration_seconds: int = 10
    player_taps: Dict[str, int] = {}
    last_tap_times: Dict[str, float] = {}
    max_taps_per_second: int = 20  # Anti-cheat rate limit
    server_prompts: Dict[str, List[float]] = {}  # Random server validation prompts

# Impostor Prompt specific data
class ImpostorPromptData(BaseGameData):
    game_type: Literal[GameType.IMPOSTOR_PROMPT] = GameType.IMPOSTOR_PROMPT
    discussion_duration: int = 60
    real_prompt: str = ""
    decoy_prompt: str = ""
    impostors: List[str] = []
    votes: Dict[str, str] = {}  # voter -> voted_for
    revealed: bool = False

# Buzzer Trivia specific data
class BuzzerTriviaData(BaseGameData):
    game_type: Literal[GameType.BUZZER_TRIVIA] = GameType.BUZZER_TRIVIA
    category_options: List[str] = []  # Categories to vote on
    category_votes: Dict[str, str] = {}  # player -> category_voted_for
    selected_category: str = ""  # Winning category
    current_question: str = ""  # The trivia question
    correct_answer: str = ""  # The correct answer
    buzzers: List[Dict[str, Any]] = []  # [{"player": "name", "time": 123.45, "position": 1}]
    current_round: int = 1
    max_rounds: int = 3
    round_scores: Dict[str, int] = {}  # player -> points this round
    total_scores: Dict[str, int] = {}  # player -> total points

# Shotgun Roulette specific data
class ShotgunRouletteData(BaseGameData):
    game_type: Literal[GameType.SHOTGUN_ROULETTE] = GameType.SHOTGUN_ROULETTE
    chambers: List[bool] = []  # True = blast, False = blank
    current_round: int = 1
    eliminated_players: List[str] = []
    chamber_picks: Dict[str, int] = {}  # player -> chamber_index

# Union type for all game data
GameData = Union[TapGauntletData, BuzzerTriviaData, ImpostorPromptData, ShotgunRouletteData]

# WebSocket Event Models
class WSEventType(str, Enum):
    # Client -> Server
    PLAYER_READY = "player_ready"
    PLAYER_UNREADY = "player_unready"
    CHAT = "chat"
    GAME_ACTION = "game_action"
    PING = "ping"
    
    # Server -> Client
    LOBBY_UPDATED = "lobby_updated"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    GAME_STARTED = "game_started"
    GAME_STATE = "game_state"
    GAME_FINISHED = "game_finished"
    CHAT_MESSAGE = "chat_message"
    TICK = "tick"
    PONG = "pong"
    ERROR = "error"

class WSEvent(BaseModel):
    type: WSEventType
    payload: Dict[str, Any] = {}
    timestamp: Optional[float] = None

# Client Events
class PlayerReadyEvent(BaseModel):
    player_name: str

class PlayerUnreadyEvent(BaseModel):
    player_name: str

class ChatEvent(BaseModel):
    player_name: str
    message: str

class GameActionEvent(BaseModel):
    player_name: str
    action: str
    data: Dict[str, Any] = {}

class PingEvent(BaseModel):
    timestamp: float

# Server Events
class LobbyUpdatedEvent(BaseModel):
    lobby_name: str
    players: List[Dict[str, Any]]
    game_state: Optional[GameState] = None

class PlayerJoinedEvent(BaseModel):
    player_name: str

class PlayerLeftEvent(BaseModel):
    player_name: str

class GameStartedEvent(BaseModel):
    game_type: GameType
    game_data: Dict[str, Any]

class GameStateEvent(BaseModel):
    game_data: Dict[str, Any]

class GameFinishedEvent(BaseModel):
    results: GameResults

class ChatMessageEvent(BaseModel):
    player_name: str
    message: str
    timestamp: float

class TickEvent(BaseModel):
    game_time: float
    remaining_time: float

class ErrorEvent(BaseModel):
    error: str
    code: Optional[str] = None

# Game Action Types for Tap Gauntlet
class TapAction(BaseModel):
    action: Literal["tap"] = "tap"
    timestamp: float

class TapResponseAction(BaseModel):
    action: Literal["tap_response"] = "tap_response"
    prompt_id: str
    timestamp: float

# Game Action Types for Buzzer Trivia
class VoteCategoryAction(BaseModel):
    action: Literal["vote_category"] = "vote_category"
    category: str
    timestamp: float

class BuzzerAction(BaseModel):
    action: Literal["buzz"] = "buzz"
    timestamp: float

class AwardPointsAction(BaseModel):
    action: Literal["award_points"] = "award_points"
    player_name: str
    points: int
    timestamp: float

class NextQuestionAction(BaseModel):
    action: Literal["next_question"] = "next_question"
    timestamp: float

# Start Game Request
class StartGameRequest(BaseModel):
    game_type: GameType
    host_token: Optional[str] = None
