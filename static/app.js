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
        this._isHost = false;
        this.hostToken = null;
        this.hasBuzzed = false;
        this.currentBuzzers = []; // Store current round's buzzer data
        
        this.init();
    }
    
    init() {
        // Only initialize if DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initDOM());
        } else {
            this.initDOM();
        }
    }
    
    initDOM() {
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
        console.log(`Sending WebSocket message - Type: ${type}, Payload:`, payload);
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            const message = {
                type,
                payload,
                timestamp: Date.now() / 1000
            };
            console.log('WebSocket ready, sending:', message);
            this.websocket.send(JSON.stringify(message));
        } else {
            console.log('WebSocket not ready:', this.websocket ? this.websocket.readyState : 'no websocket');
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
        if (statusEl) {
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
        } else {
            console.log(`Status: ${message} (${type})`);
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
        
        this.updateStatus('Creating room...', 'info');
        
        try {
            console.log('Creating lobby:', { lobby_name: lobbyName, player_name: playerName });
            
            const lobby = await this.apiCall('/lobby/create', 'POST', {
                lobby_name: lobbyName,
                player_name: playerName
            });
            
            console.log('Lobby created successfully:', lobby);
            
            this.currentPlayer = playerName;
            this._isHost = true;
            this.hostToken = lobby.host_token;
            this.connectWebSocket(lobbyName, playerName);
            this.showScreen('lobbyScreen');
            this.updateLobbyDisplay(lobby);
            this.updateStatus(`Room "${lobbyName}" created successfully!`, 'success');
            
        } catch (error) {
            console.error('Failed to create lobby:', error);
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
            this._isHost = false;
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
        this.showScreen('gameScreen');
        
        if (payload.game_type === 'tap_gauntlet') {
            this.setupTapGauntletUI(payload);
        } else if (payload.game_type === 'buzzer_trivia') {
            this.setupBuzzerTriviaUI(payload);
        }
    }
    
    setupTapGauntletUI(payload) {
        document.getElementById('gameTitle').textContent = 'Tap Gauntlet';
        document.getElementById('tapGameArea').classList.remove('hidden');
        
        // Hide buzzer trivia elements completely
        document.getElementById('buzzerGameArea').classList.add('hidden');
        this.hideAllBuzzerPhases();
        
        this.tapCount = 0;
        document.getElementById('scoreDisplay').textContent = '0 taps';
        document.getElementById('gameTimer').textContent = `Starting in ${payload.countdown}...`;
        document.getElementById('gameStatus').textContent = 'Get ready to tap!';
        document.getElementById('tapButton').disabled = true;
    }
    
    setupBuzzerTriviaUI(payload) {
        document.getElementById('gameTitle').textContent = '🔔 Buzzer Trivia';
        document.getElementById('tapGameArea').classList.add('hidden');
        document.getElementById('buzzerGameArea').classList.remove('hidden');
        
        document.getElementById('buzzerTimer').textContent = payload.message || 'Get ready...';
        this.hideAllBuzzerPhases();
        this.hasBuzzed = false;  // Reset for new game
    }
    
    updateGameState(payload) {
        // Handle Tap Gauntlet states
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
        
        // Handle Buzzer Trivia states
        if (payload.phase === 'category_voting') {
            this.showCategoryVotingPhase(payload);
        } else if (payload.phase === 'voting_countdown') {
            this.updateVotingCountdown(payload);
        } else if (payload.phase === 'category_result') {
            this.showCategoryResult(payload);
        } else if (payload.phase === 'buzzer_question') {
            this.showBuzzerQuestion(payload);
        } else if (payload.phase === 'buzzer_active') {
            this.showBuzzerActive(payload);
        } else if (payload.phase === 'player_buzzed') {
            this.showPlayerBuzzed(payload);
                    } else if (payload.phase === 'live_buzzers') {
                console.log(`LIVE BUZZERS EVENT - Player: ${this.currentPlayer}, hasBuzzed before: ${this.hasBuzzed}`);
                this.showLiveBuzzers(payload);
                console.log(`LIVE BUZZERS EVENT - Player: ${this.currentPlayer}, hasBuzzed after: ${this.hasBuzzed}`);
            } else if (payload.phase === 'buzzer_cleared') {
                // CRITICAL: Reset hasBuzzed state when buzzers are cleared (new question)
                // This implements the open-source pattern for repeat buzz-ins
                console.log(`🔄 BUZZER CLEARED EVENT - Resetting hasBuzzed for ${this.currentPlayer}`);
                console.log(`hasBuzzed before reset: ${this.hasBuzzed}`);
                this.hasBuzzed = false;
                console.log(`hasBuzzed after reset: ${this.hasBuzzed}`);
                
                // Re-enable the buzzer button
                const buzzerButton = document.getElementById('buzzerButton');
                if (buzzerButton) {
                    buzzerButton.disabled = false;
                    buzzerButton.style.backgroundColor = '#22c55e'; // Green
                    buzzerButton.textContent = 'BUZZ IN!';
                }
                
                // Clear buzz status
                const buzzStatus = document.getElementById('buzzStatus');
                if (buzzStatus) {
                    buzzStatus.textContent = '';
                }
                
                console.log(`✅ ${this.currentPlayer} ready to buzz again!`);
            } else if (payload.phase === 'buzzer_countdown') {
            this.updateCountdown(payload);
        } else if (payload.phase === 'host_judging') {
            this.showHostJudging(payload);
        } else if (payload.phase === 'host_answer') {
            this.showHostAnswer(payload);
        } else if (payload.phase === 'points_awarded') {
            this.showPointsAwarded(payload);
        } else if (payload.phase === 'next_question') {
            this.showNextQuestion(payload);
        } else if (payload.phase === 'buzzer_results') {
            this.showBuzzerResults(payload);
        } else if (payload.phase === 'timeout') {
            this.showTimeout(payload);
        } else if (payload.phase === 'question_updated') {
            this.showQuestionUpdated(payload);
        }
        
        if (payload.category_vote_confirmed) {
            document.getElementById('categoryVotingStatus').textContent = `✅ Voted for ${payload.voted_category}!`;
        }
        
        if (payload.buzz_confirmed) {
            document.getElementById('buzzStatus').textContent = '✅ Buzzed in!';
            document.getElementById('buzzerButton').disabled = true;
        }
    }
    
    hideAllBuzzerPhases() {
        document.getElementById('categoryVotingPhase').classList.add('hidden');
        document.getElementById('questionPhase').classList.add('hidden');
        document.getElementById('hostJudgingPhase').classList.add('hidden');
        document.getElementById('buzzerResultsPhase').classList.add('hidden');
        document.getElementById('buzzerSection').classList.add('hidden');
        document.getElementById('liveBuzzerList').classList.add('hidden');
        document.getElementById('hostAnswerSection').classList.add('hidden');
        document.getElementById('countdownDisplay').classList.add('hidden');
    }
    
    showCategoryVotingPhase(payload) {
        this.hideAllBuzzerPhases();
        document.getElementById('categoryVotingPhase').classList.remove('hidden');
        
        document.getElementById('buzzerTimer').textContent = payload.message;
        
        // Show countdown if provided
        if (payload.countdown !== undefined) {
            document.getElementById('countdownDisplay').classList.remove('hidden');
            document.getElementById('countdownNumber').textContent = payload.countdown;
        }
        
        const categoriesList = document.getElementById('categoriesList');
        categoriesList.innerHTML = '';
        
        payload.categories.forEach(category => {
            const button = document.createElement('button');
            button.textContent = category;
            button.style.cssText = 'width: 100%; margin: 8px 0; padding: 12px; font-size: 16px;';
            button.onclick = () => this.voteForCategory(category);
            categoriesList.appendChild(button);
        });
        
        document.getElementById('categoryVotingStatus').textContent = '';
    }
    
    updateVotingCountdown(payload) {
        document.getElementById('buzzerTimer').textContent = payload.message;
        
        // Update countdown display
        const countdownDisplay = document.getElementById('countdownDisplay');
        if (countdownDisplay.classList.contains('hidden') && payload.countdown !== undefined) {
            countdownDisplay.classList.remove('hidden');
        }
        
        const countdownEl = document.getElementById('countdownNumber');
        if (countdownEl && payload.countdown !== undefined) {
            countdownEl.textContent = payload.countdown;
            // Update color based on remaining time
            if (payload.countdown <= 5) {
                countdownEl.style.color = '#e53e3e';
                countdownEl.style.transform = 'scale(1.2)';
            } else {
                countdownEl.style.color = '#ff6b6b';
                countdownEl.style.transform = 'scale(1)';
            }
        }
    }
    
    showCategoryResult(payload) {
        document.getElementById('buzzerTimer').textContent = payload.message;
    }
    
    showBuzzerQuestion(payload) {
        console.log(`showBuzzerQuestion - Player: ${this.currentPlayer}, hasBuzzed before: ${this.hasBuzzed}`);
        
        // CRITICAL: Force reset hasBuzzed state
        this.hasBuzzed = false;
        console.log(`FORCED hasBuzzed reset to FALSE for ${this.currentPlayer}`);
        
        this.hideAllBuzzerPhases();
        document.getElementById('questionPhase').classList.remove('hidden');
        
        document.getElementById('triviaCategory').textContent = `Category: ${payload.category}`;
        document.getElementById('triviaQuestion').textContent = payload.question;
        document.getElementById('buzzerTimer').textContent = payload.message;
        document.getElementById('buzzStatus').textContent = '';
        
        console.log(`showBuzzerQuestion complete - ${this.currentPlayer} hasBuzzed: ${this.hasBuzzed}`);
    }
    
    showBuzzerActive(payload) {
        console.log(`Buzzer active - Player: ${this.currentPlayer}, hasBuzzed: ${this.hasBuzzed}, isHost: ${this.isHost}`);
        document.getElementById('buzzerSection').classList.remove('hidden');
        document.getElementById('buzzerTimer').textContent = payload.message;
        document.getElementById('buzzerButton').disabled = false;
        document.getElementById('buzzerButton').style.background = '#ff6b6b';
        
        // Always show countdown display during buzzer phase
        document.getElementById('countdownDisplay').classList.remove('hidden');
        
        // Show countdown if provided
        if (payload.countdown_seconds) {
            document.getElementById('countdownNumber').textContent = payload.countdown_seconds;
            this.startCountdown(payload.countdown_seconds);
        }
        
        console.log('Buzzer button enabled for all players');
    }
    
    showPlayerBuzzed(payload) {
        if (payload.buzzer_player !== this.currentPlayer) {
            document.getElementById('buzzerButton').disabled = true;
            document.getElementById('buzzerButton').style.background = '#666';
        }
        document.getElementById('buzzerTimer').textContent = payload.message;
    }
    
    showLiveBuzzers(payload) {
        // Check if WebSocket is still connected
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            console.log('⚠️ Ignoring buzzer update - WebSocket disconnected');
            return;
        }
        
        console.log('Live buzzers update:', payload.buzzers);
        console.log('RAW BUZZER DATA:', JSON.stringify(payload.buzzers, null, 2));
        
        // DEBUG: Log each buzzer's time and player for sorting debug
        if (payload.buzzers) {
            payload.buzzers.forEach((buzzer, i) => {
                console.log(`BUZZER ${i}: player=${buzzer.player}, time=${buzzer.time}, position=${buzzer.position}`);
            });
        }
        console.log('Showing live buzzer list...');
        document.getElementById('buzzerTimer').textContent = payload.message;
        
        // Show live buzzer list but keep buzzer active for others
        const liveBuzzerList = document.getElementById('liveBuzzerList');
        liveBuzzerList.classList.remove('hidden');
        console.log('Live buzzer list element:', liveBuzzerList, 'visible:', !liveBuzzerList.classList.contains('hidden'));
        
        const liveBuzzersDiv = document.getElementById('liveBuzzers');
        liveBuzzersDiv.innerHTML = '';
        console.log('Cleared buzzer list content');
        
        if (payload.buzzers && payload.buzzers.length > 0) {
            console.log(`Processing ${payload.buzzers.length} buzzers`);
            // Sort by time (earliest first) to get correct order
            const sortedBuzzers = [...payload.buzzers].sort((a, b) => a.time - b.time);
            console.log('Sorted buzzers:', sortedBuzzers);
            
            sortedBuzzers.forEach((buzzer, index) => {
                console.log(`Creating buzzer item for ${buzzer.player} at position ${index + 1}`);
                const buzzerDiv = document.createElement('div');
                buzzerDiv.className = 'result-item';
                const position = index + 1; // Use sorted position for live display
                const medal = position === 1 ? '🥇' : position === 2 ? '🥈' : position === 3 ? '🥉' : `${position}.`;
                const timeMs = Date.now() - (buzzer.time * 1000);
                const timeDisplay = timeMs < 1000 ? 'just now' : `${(timeMs / 1000).toFixed(1)}s ago`;
                
                buzzerDiv.innerHTML = `
                    <span>${medal} ${buzzer.player}</span>
                    <span>${timeDisplay}</span>
                `;
                liveBuzzersDiv.appendChild(buzzerDiv);
                console.log('Added buzzer div:', buzzerDiv);
            });
            console.log('Final buzzer list HTML:', liveBuzzersDiv.innerHTML);
        } else {
            console.log('No buzzers to display');
        }
        
        // Update countdown if provided
        if (payload.countdown !== undefined) {
            this.updateCountdown({countdown: payload.countdown, message: payload.message});
        }
        
        // Keep buzzer active for players who haven't buzzed yet
        if (payload.keep_buzzing && !payload.buzzers.some(b => b.player === this.currentPlayer)) {
            document.getElementById('buzzerButton').disabled = false;
            document.getElementById('buzzerButton').style.background = '#ff6b6b';
            document.getElementById('buzzerSection').classList.remove('hidden');
        }
    }
    
    showHostJudging(payload) {
        console.log('Host judging - final buzzers:', payload.buzzers);
        this.hideAllBuzzerPhases();
        document.getElementById('hostJudgingPhase').classList.remove('hidden');
        
        document.getElementById('buzzerTimer').textContent = payload.message;
        
        // Store buzzer data for host controls
        this.currentBuzzers = payload.buzzers || [];
        
        const orderDiv = document.getElementById('buzzerOrder');
        orderDiv.innerHTML = '';
        
        // Show question only (no answer for players)
        const questionDiv = document.createElement('div');
        questionDiv.style.marginBottom = '16px';
        questionDiv.innerHTML = `<p><strong>Q:</strong> ${payload.question}</p>`;
        orderDiv.appendChild(questionDiv);
        
        // Show buzzer order with times
        if (payload.buzzers && payload.buzzers.length > 0) {
            const buzzersDiv = document.createElement('div');
            buzzersDiv.innerHTML = '<h4>Final Buzzer Order:</h4>';
            
            payload.buzzers.forEach((buzzer) => {
                const buzzerDiv = document.createElement('div');
                buzzerDiv.className = 'result-item';
                const position = buzzer.position || 1;
                const medal = position === 1 ? '🥇' : position === 2 ? '🥈' : position === 3 ? '🥉' : `${position}.`;
                const suffix = position === 1 ? 'st' : position === 2 ? 'nd' : position === 3 ? 'rd' : 'th';
                buzzerDiv.innerHTML = `
                    <span>${medal} ${buzzer.player}</span>
                    <span>Buzzed ${position}${suffix}</span>
                `;
                buzzersDiv.appendChild(buzzerDiv);
            });
            
            orderDiv.appendChild(buzzersDiv);
        }
    }
    
    showHostAnswer(payload) {
        // This is only sent to the host
        if (payload.host_controls) {
            document.getElementById('hostAnswerSection').classList.remove('hidden');
            document.getElementById('hostAnswer').textContent = payload.correct_answer;
            document.getElementById('hostControls').classList.remove('hidden');
            
            // Setup host controls based on stored buzzer data
            if (this.currentBuzzers && this.currentBuzzers.length > 0) {
                this.setupHostControls(this.currentBuzzers);
            }
        }
    }
    
    setupHostControls(buzzers) {
        console.log('Setting up host controls with buzzers:', buzzers);
        const pointButtonsDiv = document.getElementById('pointButtons');
        pointButtonsDiv.innerHTML = '';
        
        if (buzzers && buzzers.length > 0) {
            console.log(`Creating ${buzzers.length} point buttons`);
            buzzers.forEach(buzzer => {
                const button = document.createElement('button');
                button.textContent = `Give ${buzzer.player} 1 point`;
                button.style.cssText = 'width: 100%; margin: 4px 0; padding: 8px; background: #48bb78; color: white; border: none; border-radius: 4px; cursor: pointer;';
                button.onclick = () => {
                    console.log(`Awarding 1 point to ${buzzer.player}`);
                    this.awardPoints(buzzer.player, 1);
                };
                pointButtonsDiv.appendChild(button);
            });
        } else {
            console.log('No buzzers found for host controls');
        }
    }
    
    showPointsAwarded(payload) {
        document.getElementById('buzzerTimer').textContent = payload.message;
        
        // Update scoreboard if visible
        if (payload.total_scores) {
            console.log('Updated scores:', payload.total_scores);
        }
    }
    
    showNextQuestion(payload) {
        console.log('showNextQuestion called - payload:', payload);
        
        // Reset hasBuzzed state first
        this.hasBuzzed = false;
        console.log('hasBuzzed reset to false for next question');
        
        // Hide current phases and show the new question
        this.hideAllBuzzerPhases();
        
        // Update the question if provided
        if (payload.question) {
            document.getElementById('triviaQuestion').textContent = payload.question;
        }
        
        // Show the new question UI
        this.showBuzzerQuestion(payload);
        
        console.log('Next question setup complete');
    }
    
    showBuzzerResults(payload) {
        this.hideAllBuzzerPhases();
        document.getElementById('buzzerResultsPhase').classList.remove('hidden');
        
        document.getElementById('buzzerTimer').textContent = payload.message;
        
        const resultsDiv = document.getElementById('buzzerResults');
        resultsDiv.innerHTML = '';
        
        // Show round summary
        if (payload.total_scores) {
            const scoresDiv = document.createElement('div');
            scoresDiv.innerHTML = '<h4>Current Scores:</h4>';
            
            Object.entries(payload.total_scores)
                .sort(([,a], [,b]) => b - a)
                .forEach(([player, score]) => {
                    const scoreDiv = document.createElement('div');
                    scoreDiv.className = 'result-item';
                    scoreDiv.innerHTML = `<span>${player}</span><span>${score} points</span>`;
                    scoresDiv.appendChild(scoreDiv);
                });
            
            resultsDiv.appendChild(scoresDiv);
        }
    }
    
    showTimeout(payload) {
        document.getElementById('buzzerTimer').textContent = payload.message;
        document.getElementById('buzzerButton').disabled = true;
        document.getElementById('buzzerButton').style.background = '#666';
    }
    
    showQuestionUpdated(payload) {
        // Update the question display
        document.getElementById('triviaQuestion').textContent = payload.question;
        document.getElementById('buzzerTimer').textContent = payload.message;
        
        // Show a notification that the question was updated
        const statusEl = document.getElementById('buzzStatus');
        if (statusEl) {
            statusEl.textContent = '🤖 Host generated a new AI question!';
            statusEl.className = 'status success';
        }
        
        console.log('Question updated:', payload.question);
        console.log('AI Source:', payload.source);
    }
    
    voteForCategory(category) {
        this.sendWebSocketMessage('game_action', {
            action: 'vote_category',
            category: category,
            timestamp: Date.now() / 1000
        });
        
        document.getElementById('categoryVotingStatus').textContent = `Voting for ${category}...`;
    }
    
    buzz() {
        console.log(`==== BUZZ ATTEMPT (${Date.now()}) ====`);
        console.log(`Player: ${this.currentPlayer}`);
        console.log(`Is Host: ${this.isHost}`);
        console.log(`hasBuzzed before check: ${this.hasBuzzed}`);
        console.log(`WebSocket state: ${this.websocket ? this.websocket.readyState : 'no websocket'}`);
        
        if (this.hasBuzzed) {
            console.log('❌ BUZZ BLOCKED - already buzzed (this should not happen for host after reset)');
            console.log('CURRENT hasBuzzed value:', this.hasBuzzed);
            return;
        }
        
        console.log('✅ BUZZ ALLOWED - setting hasBuzzed to true and sending');
        this.hasBuzzed = true;  // Set immediately to prevent double-clicks
        
        console.log('📡 Sending buzz WebSocket message...');
        this.sendWebSocketMessage('game_action', {
            action: 'buzz',
            player: this.currentPlayer,
            timestamp: Date.now() / 1000
        });
        
        document.getElementById('buzzStatus').textContent = 'Buzzing in...';
        document.getElementById('buzzerButton').disabled = true;
        console.log('🔘 Buzz sent and button disabled');
        console.log(`==== BUZZ COMPLETE ====`);
    }
    
    awardPoints(playerName, points) {
        console.log(`Sending award_points action: ${playerName} gets ${points} points`);
        this.sendWebSocketMessage('game_action', {
            action: 'award_points',
            player_name: playerName,
            points: points,
            timestamp: Date.now() / 1000
        });
    }
    
    nextQuestion() {
        this.sendWebSocketMessage('game_action', {
            action: 'next_question',
            timestamp: Date.now() / 1000
        });
    }
    
    endGame() {
        if (confirm('Are you sure you want to end the game and return to lobby?')) {
            this.sendWebSocketMessage('game_action', {
                action: 'end_game',
                timestamp: Date.now() / 1000
            });
        }
    }
    
    // AI Question generation removed - using static question bank only
    
    startCountdown(seconds) {
        // Visual countdown display
        this.countdownInterval = setInterval(() => {
            const countdownEl = document.getElementById('countdownNumber');
            if (countdownEl) {
                const current = parseInt(countdownEl.textContent) - 1;
                if (current > 0) {
                    countdownEl.textContent = current;
                    // Change color as time runs out
                    if (current <= 5) {
                        countdownEl.style.color = '#e53e3e';
                        countdownEl.style.transform = 'scale(1.2)';
                    }
                } else {
                    clearInterval(this.countdownInterval);
                    document.getElementById('countdownDisplay').classList.add('hidden');
                }
            }
        }, 1000);
    }
    
    updateCountdown(payload) {
        document.getElementById('buzzerTimer').textContent = payload.message;
        
        // Show countdown display if not visible
        const countdownDisplay = document.getElementById('countdownDisplay');
        if (countdownDisplay.classList.contains('hidden') && payload.countdown !== undefined) {
            countdownDisplay.classList.remove('hidden');
        }
        
        const countdownEl = document.getElementById('countdownNumber');
        if (countdownEl && payload.countdown !== undefined) {
            countdownEl.textContent = payload.countdown;
            // Update color based on remaining time
            if (payload.countdown <= 5) {
                countdownEl.style.color = '#e53e3e';
                countdownEl.style.transform = 'scale(1.2)';
            } else {
                countdownEl.style.color = '#ff6b6b';
                countdownEl.style.transform = 'scale(1)';
            }
        }
        
        // Keep buzzer active if specified
        if (payload.keep_buzzing && !this.hasBuzzed) {
            document.getElementById('buzzerButton').disabled = false;
            document.getElementById('buzzerButton').style.background = '#ff6b6b';
            document.getElementById('buzzerSection').classList.remove('hidden');
        }
    }
    
    get isHost() {
        return this._isHost && this.currentLobby && this.currentLobby.host === this.currentPlayer;
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
        
        if (results.game_type === 'buzzer_trivia') {
            resultsEl.innerHTML = '<h3>🔔 Buzzer Trivia Results</h3>';
            
            results.scores.forEach(score => {
                const resultEl = document.createElement('div');
                resultEl.className = 'result-item';
                if (score.position === 1) {
                    resultEl.classList.add('winner');
                }
                
                resultEl.innerHTML = `
                    <span>#${score.position} ${score.player_name}</span>
                    <span>${score.score} points</span>
                `;
                
                resultsEl.appendChild(resultEl);
            });
            
            if (results.winner) {
                this.updateStatus(`🏆 ${results.winner} wins Buzzer Trivia with ${results.scores[0].score} points!`, 'success');
            }
        } else {
            // Tap Gauntlet results
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
    if (window.gameClient) {
        window.gameClient.createLobby();
    } else {
        console.error('Game client not initialized');
    }
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

function buzz() {
    window.gameClient.buzz();
}

function nextQuestion() {
    window.gameClient.nextQuestion();
}

function endGame() {
    window.gameClient.endGame();
}

// AI Question generation removed

// Initialize the game client immediately
window.gameClient = new GameClient();

// Also ensure it's available when DOM loads
window.addEventListener('DOMContentLoaded', () => {
    if (!window.gameClient) {
        window.gameClient = new GameClient();
    }
});
