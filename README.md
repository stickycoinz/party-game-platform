# 🎮 Party Game Platform

A lightweight, browser-based party game platform where players create rooms, join via codes, and play real-time games together. Built with FastAPI and WebSockets for low-latency multiplayer gaming.

## 🚀 Features

### ✅ Sprint 1 (Completed - Deployed Live!)
- **REST API**: Create, join, ready up, and start games
- **WebSocket Real-time**: Live lobby updates and game state synchronization
- **Tap Gauntlet Game**: 10-second tapping competition with anti-cheat measures
- **Test Client**: Beautiful HTML/JS interface for testing and demos
- **Validation**: Comprehensive input validation and error handling

### 🔜 Sprint 2 (Planned)
- **Room Discovery**: Public room list for easy joining
- **Additional Games**: Impostor Prompt, Shotgun Roulette
- **Redis Backend**: Scalable state management for production
- **Mobile Optimization**: Touch-friendly UI with haptic feedback
- **Match History**: Persistent game results with Postgres

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.11+) with Uvicorn
- **Validation**: Pydantic v2 models with comprehensive schemas
- **Real-time**: FastAPI WebSockets with connection management
- **State**: In-memory storage (Redis-ready architecture)
- **Frontend**: Vanilla HTML/CSS/JavaScript (framework-agnostic)
- **Deployment**: Docker + fly.io/Render/Hetzner ready

## 📁 Project Structure

```
party_game_app/
├── app/
│   ├── main.py                 # FastAPI app factory
│   ├── routers/
│   │   ├── lobby_routes.py     # REST endpoints
│   │   ├── ws_routes.py        # WebSocket handlers
│   │   └── game_logic.py       # Game implementations
│   ├── schemas/
│   │   ├── lobby.py            # Lobby & player models
│   │   └── game.py             # Game state & events
│   └── utils/
│       ├── ids.py              # ID generation & validation
│       ├── errors.py           # Error factories
│       └── storage.py          # Storage abstraction
├── static/
│   ├── index.html              # Test client UI
│   └── app.js                  # Client-side logic
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🎯 Game Modes

### Tap Gauntlet (10s)
- **Objective**: Tap as fast as possible in 10 seconds
- **Anti-cheat**: Server-side rate limiting and random validation prompts
- **Scoring**: Total taps with position rankings
- **Min Players**: 2, Max: 12

### Coming Soon
- **Impostor Prompt**: Social deduction with decoy prompts
- **Shotgun Roulette**: Fast-paced elimination game

## 🚀 Quick Start

### Local Development

1. **Install Dependencies**
```bash
cd party_game_app
pip install -r requirements.txt
```

2. **Run the Server**
```bash
uvicorn app.main:app --reload
```

3. **Access the App**
- **API Docs**: http://127.0.0.1:8000/docs
- **Test Client**: http://127.0.0.1:8000/static/index.html
- **Health Check**: http://127.0.0.1:8000/health

### Testing with Multiple Players

1. Open the test client in multiple browser tabs/windows
2. Create a room with one tab (you become the host)
3. Join the same room from other tabs with different names
4. Ready up all players
5. Start a Tap Gauntlet game and compete!

## 📡 API Reference

### REST Endpoints

#### Create Lobby
```http
POST /lobby/create
Content-Type: application/json

{
  "lobby_name": "MyRoom",
  "player_name": "Alice"
}
```

#### Join Lobby
```http
POST /lobby/join
Content-Type: application/json

{
  "lobby_name": "MyRoom", 
  "player_name": "Bob"
}
```

#### Ready Up
```http
POST /lobby/{lobby_name}/ready?player_name=Alice
```

#### Start Game
```http
POST /lobby/{lobby_name}/start
Content-Type: application/json

{
  "game_type": "tap_gauntlet",
  "host_token": "abc123"
}
```

#### Get Lobby Info
```http
GET /lobby/{lobby_name}
```

#### List All Lobbies
```http
GET /lobby/
```

### WebSocket Events

#### Client → Server
- `player_ready` / `player_unready`: Toggle ready state
- `chat`: Send chat message
- `game_action`: Game-specific actions (e.g., tap)
- `ping`: Connection health check

#### Server → Client
- `lobby_updated`: Lobby state changed
- `player_joined` / `player_left`: Player events
- `game_started`: Game initialization
- `game_state`: Real-time game updates
- `game_finished`: Results and scoring
- `tick`: Timer and score updates

## 🔧 Configuration

### Environment Variables (Future)
```bash
REDIS_URL=redis://localhost:6379/0
REGION=us-west
DEBUG=true
```

### Game Settings
- **Max Players**: 12 per lobby
- **Tap Rate Limit**: 20 taps/second (anti-cheat)
- **Game Duration**: 10 seconds (Tap Gauntlet)
- **Connection Timeout**: Auto-disconnect after inactivity

## 🏗️ Architecture

### State Management
- **Development**: In-memory dictionaries with asyncio locks
- **Production**: Redis with pub/sub for horizontal scaling
- **Storage Interface**: Abstract backend for easy swapping

### Real-time Communication
- **WebSocket per Lobby**: Isolated connection pools
- **Event Broadcasting**: Efficient message fan-out
- **Connection Management**: Automatic cleanup and reconnection

### Anti-cheat Measures
- **Server-side Validation**: All game state on backend
- **Rate Limiting**: Max actions per second per player
- **Random Prompts**: Periodic validation challenges
- **Tick Windows**: Server-controlled timing

## 🌐 Deployment

### Docker Setup (Coming Soon)
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ ./app/
COPY static/ ./static/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- **Regional Deployment**: US-West + EU-West for latency
- **Load Balancing**: Session affinity for WebSocket connections
- **Monitoring**: Health checks and error tracking
- **Rate Limiting**: Per-IP and per-lobby throttling

## 🎮 Usage Flow

1. **Setup**: Player enters display name
2. **Create/Join**: Host creates room, others join by name
3. **Lobby**: Players see each other, ready up when prepared
4. **Game**: Host starts when all ready, real-time gameplay
5. **Results**: Scores displayed, option to play again

## 🐛 Error Handling

### HTTP Error Codes
- `400`: Invalid input, duplicate names/lobbies
- `404`: Lobby or player not found
- `409`: Game state conflicts, not ready
- `403`: Host-only actions

### WebSocket Close Codes
- `4004`: Lobby not found
- `4009`: Player kicked/removed
- `4010`: Duplicate name conflict

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details.

## 🎯 Roadmap

- [ ] Redis storage backend
- [ ] Additional game modes
- [ ] Mobile-first UI improvements
- [ ] Spectator mode
- [ ] Tournament brackets
- [ ] Custom game durations
- [ ] Voice chat integration
- [ ] Replay system
