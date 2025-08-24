// Party Game Platform - Test Client JavaScript

class GameClient {
    constructor() {
        this.apiBase = window.location.origin;
        this.wsBase = window.location.origin.replace('http', 'ws');
        this.currentLobby = null;
        this.currentPlayer = null;
        this.websocket = null;
        this.gameState = 'setup';
        this.tapCount = 0;
        this.gameTimer = null;
        this.lastTapTime = 0;
        this.isHost = false;
        this.hostToken = null;
        
        this.init();
    }
    
    init() {
        this.updateStatus('Welcome! Enter your name to get started.');
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Enter key handlers
        document.getElementById('playerName').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const name = e.target.value.trim();
                if (name) this.updateStatus(`Ready to play, ${name}!`);
            }
        });
        
        document.getElementById('lobbyName').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.createLobby();
        });
        
        document.getElementById('joinLobbyName').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.joinLobby();
        });
        
        // Prevent double-tap zoom on mobile
        document.getElementById('tapButton').addEventListener('touchstart', (e) => {
            e.preventDefault();
        });
    }
    
    // API Methods
    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            const response = await fetch(`${this.apiBase}${endpoint}`, options);
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.detail || 'API Error');
            }
            
            return result;
        } catch (error) {
            this.updateStatus(`Error: ${error.message}`, 'error');
            throw error;
        }
    }
    
    // WebSocket Methods
    connectWebSocket(lobbyName, playerName) {
        if (this.websocket) {
            this.websocket.close();
        }
        
        const wsUrl = `${this.wsBase}/ws/lobby/${lobbyName}?player_name=${encodeURIComponent(playerName)}`;
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            this.updateWSStatus(true);
            this.updateStatus('Connected to lobby!', 'success');
        };
        
        this.websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
        };
        
        this.websocket.onclose = (event) => {
            this.updateWSStatus(false);
            if (event.code === 4004) {
                this.updateStatus('Lobby not found', 'error');
                this.backToSetup();
            } else if (event.code === 4009) {
                this.updateStatus('You were removed from the lobby', 'error');
                this.backToSetup();
            } else {
                this.updateStatus('Disconnected from lobby', 'error');
            }
        };
        
        this.websocket.onerror = (error) => {
            this.updateStatus('Connection error', 'error');
        };
    }
    
    sendWebSocketMessage(type, payload = {}) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type,
                payload,
                timestamp: Date.now() / 1000
            }));
        }
    }
    
    handleWebSocketMessage(message) {
        const { type, payload, timestamp } = message;
        
        switch (type) {
            case 'lobby_updated':
                this.updateLobbyDisplay(payload.lobby);
                break;
                
            case 'player_joined':
                this.updateStatus(`${payload.player_name} joined the lobby`, 'info');
                break;
                
            case 'player_left':
                this.updateStatus(`${payload.player_name} left the lobby`, 'info');
                break;
                
            case 'game_started':
                this.startGameUI(payload);
                break;
                
            case 'game_state':
                this.updateGameState(payload);
                break;
                
            case 'game_finished':
                this.showResults(payload.results);
                break;
                
            case 'tick':
                this.updateGameTick(payload);
                break;
                
            case 'chat_message':
                this.updateStatus(`${payload.player_name}: ${payload.message}`, 'info');
                break;
                
            case 'error':
                this.updateStatus(`Error: ${payload.error}`, 'error');
                break;
        }
    }
    
    // UI Methods
    showScreen(screenId) {
        const screens = ['setupScreen', 'lobbyScreen', 'gameScreen', 'resultsScreen'];
        screens.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.classList.toggle('hidden', id !== screenId);
            }
        });
    }
    
    updateStatus(message, type = 'info') {
        const statusEl = document.getElementById('statusMessage');
        statusEl.textContent = message;
        statusEl.className = `status ${type}`;
        
        // Auto-clear non-error messages
        if (type !== 'error') {
            setTimeout(() => {
                if (statusEl.textContent === message) {
                    statusEl.textContent = '';
                }
            }, 5000);
        }
    }
    
    updateWSStatus(connected) {
        const statusEl = document.getElementById('wsStatus');
        statusEl.textContent = connected ? 'Connected' : 'Disconnected';
        statusEl.className = `ws-status ${connected ? 'ws-connected' : 'ws-disconnected'}`;
    }
    
    updateLobbyDisplay(lobby) {
        this.currentLobby = lobby;
        
        document.getElementById('lobbyTitle').textContent = `Room: ${lobby.lobby_name}`;
        
        const playersEl = document.getElementById('playersList');
        playersEl.innerHTML = '';
        
        lobby.players.forEach(player => {
            const playerEl = document.createElement('div');
            playerEl.className = 'player';
            
            const nameEl = document.createElement('div');
            nameEl.className = 'player-name';
            nameEl.textContent = player.name;
            
            if (player.name === lobby.host) {
                const hostBadge = document.createElement('span');
                hostBadge.className = 'host-badge';
                hostBadge.textContent = 'HOST';
                nameEl.appendChild(hostBadge);
            }
            
            const statusEl = document.createElement('div');
            statusEl.className = `player-status ${player.is_ready ? 'ready' : 'not-ready'}`;
            statusEl.textContent = player.is_ready ? 'Ready' : 'Not Ready';
            
            playerEl.appendChild(nameEl);
            playerEl.appendChild(statusEl);
            playersEl.appendChild(playerEl);
        });
        
        // Update ready button
        const readyButton = document.getElementById('readyButton');
        const currentPlayer = lobby.players.find(p => p.name === this.currentPlayer);
        if (currentPlayer) {
            readyButton.textContent = currentPlayer.is_ready ? 'Not Ready' : 'Ready Up';
        }
        
        // Show start button for host
        const startButton = document.getElementById('startButton');
        const allReady = lobby.players.every(p => p.is_ready);
        const canStart = this.isHost && allReady && lobby.players.length >= 2;
        
        console.log('Start button check:', {
            isHost: this.isHost,
            allReady: allReady,
            playerCount: lobby.players.length,
            canStart: canStart,
            currentPlayer: this.currentPlayer,
            host: lobby.host
        });
        
        startButton.classList.toggle('hidden', !canStart);
        
        // Debug: Always show start button for testing (remove this later)
        if (lobby.players.length >= 2 && allReady) {
            startButton.classList.remove('hidden');
            startButton.textContent = this.isHost ? 'Start Game' : 'Start Game (Any Player)';
            console.log('Showing start button for testing');
        }
    }
    
    // Game Logic
    async createLobby() {
        const playerName = document.getElementById('playerName').value.trim();
        const lobbyName = document.getElementById('lobbyName').value.trim();
        
        if (!playerName || !lobbyName) {
            this.updateStatus('Please enter both your name and room name', 'error');
            return;
        }
        
        try {
            const lobby = await this.apiCall('/lobby/create', 'POST', {
                lobby_name: lobbyName,
                player_name: playerName
            });
            
            this.currentPlayer = playerName;
            this.isHost = true;
            this.hostToken = lobby.host_token;
            this.connectWebSocket(lobbyName, playerName);
            this.showScreen('lobbyScreen');
            this.updateLobbyDisplay(lobby);
            
        } catch (error) {
            // Error already handled in apiCall
        }
    }
    
    async joinLobby() {
        const playerName = document.getElementById('playerName').value.trim();
        const lobbyName = document.getElementById('joinLobbyName').value.trim();
        
        if (!playerName || !lobbyName) {
            this.updateStatus('Please enter both your name and room name', 'error');
            return;
        }
        
        try {
            const lobby = await this.apiCall('/lobby/join', 'POST', {
                lobby_name: lobbyName,
                player_name: playerName
            });
            
            this.currentPlayer = playerName;
            this.isHost = false;
            this.connectWebSocket(lobbyName, playerName);
            this.showScreen('lobbyScreen');
            this.updateLobbyDisplay(lobby);
            
        } catch (error) {
            // Error already handled in apiCall
        }
    }
    
    toggleReady() {
        // Send the appropriate message based on current state
        const currentPlayer = this.currentLobby?.players.find(p => p.name === this.currentPlayer);
        const isCurrentlyReady = currentPlayer?.is_ready || false;
        
        const messageType = isCurrentlyReady ? 'player_unready' : 'player_ready';
        this.sendWebSocketMessage(messageType);
        
        console.log('Toggling ready state:', {
            player: this.currentPlayer,
            currentlyReady: isCurrentlyReady,
            sending: messageType
        });
    }
    
    async startGame() {
        if (!this.isHost) return;
        
        const gameType = document.getElementById('gameSelect').value;
        
        try {
            await this.apiCall(`/lobby/${this.currentLobby.lobby_name}/start`, 'POST', {
                game_type: gameType,
                host_token: this.hostToken
            });
            
        } catch (error) {
            // Error already handled in apiCall
        }
    }
    
    startGameUI(payload) {
        this.gameState = 'starting';
        this.tapCount = 0;
        this.showScreen('gameScreen');
        
        document.getElementById('gameTitle').textContent = 'Tap Gauntlet';
        document.getElementById('scoreDisplay').textContent = '0 taps';
        document.getElementById('gameTimer').textContent = `Starting in ${payload.countdown}...`;
        document.getElementById('gameStatus').textContent = 'Get ready to tap!';
        document.getElementById('tapButton').disabled = true;
    }
    
    updateGameState(payload) {
        if (payload.state === 'in_progress') {
            this.gameState = 'playing';
            document.getElementById('gameTimer').textContent = payload.message || 'TAP NOW!';
            document.getElementById('tapButton').disabled = false;
            document.getElementById('gameStatus').textContent = 'Game in progress - TAP AS FAST AS YOU CAN!';
        }
        
        if (payload.tap_confirmed) {
            this.tapCount = payload.current_taps;
            document.getElementById('scoreDisplay').textContent = `${this.tapCount} taps`;
        }
        
        if (payload.anti_cheat_prompt) {
            // Respond to anti-cheat prompt
            this.sendWebSocketMessage('game_action', {
                action: 'tap_response',
                prompt_id: payload.anti_cheat_prompt,
                timestamp: Date.now() / 1000
            });
        }
    }
    
    updateGameTick(payload) {
        if (payload.countdown !== undefined) {
            document.getElementById('gameTimer').textContent = 
                payload.countdown > 0 ? `Starting in ${payload.countdown}...` : 'GO!';
        } else if (payload.remaining_time !== undefined) {
            document.getElementById('gameTimer').textContent = 
                `${Math.ceil(payload.remaining_time)}s remaining`;
        }
        
        if (payload.scores && this.currentPlayer && payload.scores[this.currentPlayer] !== undefined) {
            this.tapCount = payload.scores[this.currentPlayer];
            document.getElementById('scoreDisplay').textContent = `${this.tapCount} taps`;
        }
    }
    
    tap() {
        if (this.gameState !== 'playing') return;
        
        const now = Date.now();
        // Simple client-side rate limiting
        if (now - this.lastTapTime < 50) return; // Max 20 taps per second
        
        this.lastTapTime = now;
        
        this.sendWebSocketMessage('game_action', {
            action: 'tap',
            timestamp: now / 1000
        });
    }
    
    showResults(results) {
        this.gameState = 'finished';
        this.showScreen('resultsScreen');
        
        const resultsEl = document.getElementById('gameResults');
        resultsEl.innerHTML = '<h3>Final Scores</h3>';
        
        results.scores.forEach(score => {
            const resultEl = document.createElement('div');
            resultEl.className = 'result-item';
            if (score.position === 1) {
                resultEl.classList.add('winner');
            }
            
            resultEl.innerHTML = `
                <span>#${score.position} ${score.player_name}</span>
                <span>${score.score} taps</span>
            `;
            
            resultsEl.appendChild(resultEl);
        });
        
        if (results.winner) {
            this.updateStatus(`🏆 ${results.winner} wins with ${results.scores[0].score} taps!`, 'success');
        }
    }
    
    backToLobby() {
        this.gameState = 'lobby';
        this.showScreen('lobbyScreen');
        this.updateStatus('Back in lobby. Ready up for another game!', 'info');
    }
    
    leaveLobby() {
        if (this.websocket) {
            this.websocket.close();
        }
        this.backToSetup();
    }
    
    backToSetup() {
        this.currentLobby = null;
        this.currentPlayer = null;
        this.isHost = false;
        this.hostToken = null;
        this.gameState = 'setup';
        this.showScreen('setupScreen');
        
        // Clear forms
        document.getElementById('lobbyName').value = '';
        document.getElementById('joinLobbyName').value = '';
        document.getElementById('createForm').classList.add('hidden');
        document.getElementById('joinForm').classList.add('hidden');
        
        this.updateStatus('Ready to join or create a new room!', 'info');
    }
}

// UI Helper Functions
function showCreateLobby() {
    document.getElementById('createForm').classList.remove('hidden');
    document.getElementById('joinForm').classList.add('hidden');
}

function showJoinLobby() {
    document.getElementById('joinForm').classList.remove('hidden');
    document.getElementById('createForm').classList.add('hidden');
}

function createLobby() {
    window.gameClient.createLobby();
}

function joinLobby() {
    window.gameClient.joinLobby();
}

function toggleReady() {
    window.gameClient.toggleReady();
}

function startGame() {
    window.gameClient.startGame();
}

function tap() {
    window.gameClient.tap();
}

function backToLobby() {
    window.gameClient.backToLobby();
}

function leaveLobby() {
    window.gameClient.leaveLobby();
}

// Initialize the game client when page loads
window.addEventListener('DOMContentLoaded', () => {
    window.gameClient = new GameClient();
});
