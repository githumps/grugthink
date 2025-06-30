// GrugThink Dashboard JavaScript

class GrugThinkDashboard {
    constructor() {
        this.websocket = null;
        this.apiBase = '';
        this.bots = [];
        this.templates = {};
        this.tokens = [];
        
        this.initWebSocket();
        this.bindEvents();
        this.loadInitialData();
    }

    // WebSocket connection for real-time updates
    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
        };
        
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.websocket.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
            // Attempt to reconnect after 5 seconds
            setTimeout(() => this.initWebSocket(), 5000);
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('connection-status');
        if (connected) {
            indicator.innerHTML = '<i class="bi bi-circle-fill text-success"></i> Connected';
        } else {
            indicator.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> Disconnected';
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'bot_status_changed':
                this.updateBotStatus(data.data.bot_id, data.data.status);
                this.addActivityLog(`Bot ${data.data.bot_id} status changed to ${data.data.status}`);
                break;
            case 'bot_created':
                this.addActivityLog(`Bot "${data.data.name}" created`);
                this.loadBots();
                break;
            case 'bot_deleted':
                this.addActivityLog(`Bot ${data.data.bot_id} deleted`);
                this.loadBots();
                break;
            case 'config_updated':
                this.addActivityLog(`Configuration updated: ${data.data.key}`);
                break;
        }
    }

    // Event binding
    bindEvents() {
        // Add token form
        document.getElementById('add-token-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addDiscordToken();
        });

        // API keys form
        document.getElementById('api-keys-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveApiKeys();
        });

        // Tab switching
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                const target = e.target.getAttribute('href').substring(1);
                this.onTabSwitch(target);
            });
        });
    }

    onTabSwitch(tabName) {
        switch (tabName) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'bots':
                this.loadBots();
                break;
            case 'configuration':
                this.loadConfiguration();
                break;
            case 'templates':
                this.loadTemplates();
                break;
            case 'monitoring':
                this.loadLogs();
                break;
        }
    }

    // Initial data loading
    async loadInitialData() {
        await Promise.all([
            this.loadDashboard(),
            this.loadBots(),
            this.loadTemplates(),
            this.loadTokens()
        ]);
    }

    // API calls
    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(`${this.apiBase}/api${endpoint}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`API call failed: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API call error:', error);
            this.showAlert('API call failed: ' + error.message, 'danger');
            throw error;
        }
    }

    // Dashboard functions
    async loadDashboard() {
        try {
            const stats = await this.apiCall('/system/stats');
            
            document.getElementById('total-bots').textContent = stats.total_bots;
            document.getElementById('running-bots').textContent = stats.running_bots;
            document.getElementById('total-guilds').textContent = stats.total_guilds;
            document.getElementById('total-users').textContent = stats.total_users;
            
        } catch (error) {
            console.error('Failed to load dashboard:', error);
        }
    }

    async refreshDashboard() {
        await this.loadDashboard();
        this.showAlert('Dashboard refreshed', 'success');
    }

    // Bot management functions
    async loadBots() {
        try {
            this.bots = await this.apiCall('/bots');
            this.renderBotsTable();
        } catch (error) {
            console.error('Failed to load bots:', error);
        }
    }

    renderBotsTable() {
        const tbody = document.querySelector('#bots-table tbody');
        tbody.innerHTML = '';

        this.bots.forEach(bot => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <strong>${bot.name}</strong>
                    <br><small class="text-muted">ID: ${bot.bot_id}</small>
                </td>
                <td>
                    <span class="status-badge status-${bot.status}">${bot.status}</span>
                </td>
                <td>
                    <span class="badge bg-secondary personality-badge">${bot.force_personality || 'adaptive'}</span>
                </td>
                <td>${bot.guild_count || 0}</td>
                <td>${this.formatUptime(bot.last_heartbeat)}</td>
                <td>
                    <div class="btn-group btn-group-sm" role="group">
                        ${this.getBotActionButtons(bot)}
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    getBotActionButtons(bot) {
        const buttons = [];
        
        if (bot.status === 'running') {
            buttons.push(`<button class="btn btn-warning btn-action" onclick="dashboard.stopBot('${bot.bot_id}')">
                <i class="bi bi-stop-fill"></i>
            </button>`);
            buttons.push(`<button class="btn btn-info btn-action" onclick="dashboard.restartBot('${bot.bot_id}')">
                <i class="bi bi-arrow-clockwise"></i>
            </button>`);
        } else {
            buttons.push(`<button class="btn btn-success btn-action" onclick="dashboard.startBot('${bot.bot_id}')">
                <i class="bi bi-play-fill"></i>
            </button>`);
        }
        
        buttons.push(`<button class="btn btn-danger btn-action" onclick="dashboard.deleteBot('${bot.bot_id}')">
            <i class="bi bi-trash"></i>
        </button>`);
        
        return buttons.join('');
    }

    async startBot(botId) {
        try {
            await this.apiCall(`/bots/${botId}/start`, { method: 'POST' });
            this.showAlert('Bot start initiated', 'info');
            this.updateBotStatus(botId, 'starting');
        } catch (error) {
            this.showAlert('Failed to start bot', 'danger');
        }
    }

    async stopBot(botId) {
        try {
            await this.apiCall(`/bots/${botId}/stop`, { method: 'POST' });
            this.showAlert('Bot stop initiated', 'info');
            this.updateBotStatus(botId, 'stopping');
        } catch (error) {
            this.showAlert('Failed to stop bot', 'danger');
        }
    }

    async restartBot(botId) {
        try {
            await this.apiCall(`/bots/${botId}/restart`, { method: 'POST' });
            this.showAlert('Bot restart initiated', 'info');
            this.updateBotStatus(botId, 'starting');
        } catch (error) {
            this.showAlert('Failed to restart bot', 'danger');
        }
    }

    async deleteBot(botId) {
        if (!confirm('Are you sure you want to delete this bot?')) {
            return;
        }
        
        try {
            await this.apiCall(`/bots/${botId}`, { method: 'DELETE' });
            this.showAlert('Bot deleted successfully', 'success');
            this.loadBots();
        } catch (error) {
            this.showAlert('Failed to delete bot', 'danger');
        }
    }

    updateBotStatus(botId, status) {
        const bot = this.bots.find(b => b.bot_id === botId);
        if (bot) {
            bot.status = status;
            this.renderBotsTable();
            this.loadDashboard(); // Update stats
        }
    }

    // Template functions
    async loadTemplates() {
        try {
            this.templates = await this.apiCall('/templates');
            this.renderTemplates();
            this.populateTemplateSelect();
        } catch (error) {
            console.error('Failed to load templates:', error);
        }
    }

    renderTemplates() {
        const container = document.getElementById('templates-container');
        container.innerHTML = '';

        Object.entries(this.templates).forEach(([id, template]) => {
            const card = document.createElement('div');
            card.className = 'col-md-6 col-lg-4';
            card.innerHTML = `
                <div class="card template-card h-100" onclick="dashboard.selectTemplate('${id}')">
                    <div class="card-body">
                        <h5 class="card-title">${template.name}</h5>
                        <p class="card-text">${template.description}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="badge bg-primary personality-badge">
                                ${template.force_personality || 'adaptive'}
                            </span>
                            <small class="text-muted">
                                ${template.load_embedder ? 'ML Enabled' : 'Lightweight'}
                            </small>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    populateTemplateSelect() {
        const select = document.getElementById('bot-template');
        select.innerHTML = '<option value="">Select a template...</option>';
        
        Object.entries(this.templates).forEach(([id, template]) => {
            const option = document.createElement('option');
            option.value = id;
            option.textContent = `${template.name} - ${template.description}`;
            select.appendChild(option);
        });
    }

    selectTemplate(templateId) {
        document.getElementById('bot-template').value = templateId;
        const modal = new bootstrap.Modal(document.getElementById('createBotModal'));
        modal.show();
    }

    // Configuration functions
    async loadConfiguration() {
        await this.loadTokens();
        await this.loadApiKeys();
    }

    async loadTokens() {
        try {
            this.tokens = await this.apiCall('/discord-tokens');
            this.renderTokenList();
            this.populateTokenSelect();
        } catch (error) {
            console.error('Failed to load tokens:', error);
        }
    }

    renderTokenList() {
        const container = document.getElementById('token-list');
        container.innerHTML = '';

        if (this.tokens.length === 0) {
            container.innerHTML = '<p class="text-muted">No Discord tokens configured</p>';
            return;
        }

        this.tokens.forEach(token => {
            const item = document.createElement('div');
            item.className = 'token-item';
            item.innerHTML = `
                <div>
                    <div class="token-name">${token.name}</div>
                    <div class="token-meta">Added: ${new Date(token.added_at * 1000).toLocaleDateString()}</div>
                </div>
                <div>
                    <span class="badge ${token.active ? 'bg-success' : 'bg-secondary'}">${token.active ? 'Active' : 'Inactive'}</span>
                    <button class="btn btn-sm btn-danger ms-2" onclick="dashboard.deleteDiscordToken('${token.id}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            container.appendChild(item);
        });
    }

    populateTokenSelect() {
        const select = document.getElementById('bot-discord-token');
        select.innerHTML = '<option value="">Select a Discord token...</option>';
        
        this.tokens.filter(token => token.active).forEach(token => {
            const option = document.createElement('option');
            option.value = token.id;
            option.textContent = token.name;
            select.appendChild(option);
        });
    }

    async addDiscordToken() {
        const name = document.getElementById('token-name').value;
        const token = document.getElementById('discord-token').value;

        try {
            await this.apiCall('/discord-tokens', {
                method: 'POST',
                body: JSON.stringify({ name, token })
            });
            
            this.showAlert('Discord token added successfully', 'success');
            document.getElementById('add-token-form').reset();
            this.loadTokens();
        } catch (error) {
            this.showAlert('Failed to add Discord token', 'danger');
        }
    }

    async deleteDiscordToken(tokenId) {
        if (!confirm('Delete this token?')) return;

        try {
            await this.apiCall(`/discord-tokens/${tokenId}`, { method: 'DELETE' });
            this.showAlert('Token removed', 'success');
            this.loadTokens();
        } catch (error) {
            this.showAlert('Failed to remove token', 'danger');
        }
    }

    async loadApiKeys() {
        // Load and populate API key fields
        try {
            const geminiKeys = await this.apiCall('/api-keys/gemini');
            const googleKeys = await this.apiCall('/api-keys/google_search');
            
            // Note: We don't populate the actual values for security
            // Just indicate if they're set
        } catch (error) {
            console.error('Failed to load API keys:', error);
        }
    }

    async saveApiKeys() {
        const geminiKey = document.getElementById('gemini-key').value;
        const googleApiKey = document.getElementById('google-api-key').value;
        const googleCseId = document.getElementById('google-cse-id').value;

        try {
            const promises = [];
            
            if (geminiKey) {
                promises.push(this.apiCall('/api-keys', {
                    method: 'POST',
                    body: JSON.stringify({
                        service: 'gemini',
                        key_name: 'primary',
                        value: geminiKey
                    })
                }));
            }
            
            if (googleApiKey) {
                promises.push(this.apiCall('/api-keys', {
                    method: 'POST',
                    body: JSON.stringify({
                        service: 'google_search',
                        key_name: 'api_key',
                        value: googleApiKey
                    })
                }));
            }
            
            if (googleCseId) {
                promises.push(this.apiCall('/api-keys', {
                    method: 'POST',
                    body: JSON.stringify({
                        service: 'google_search',
                        key_name: 'cse_id',
                        value: googleCseId
                    })
                }));
            }
            
            await Promise.all(promises);
            this.showAlert('API keys saved successfully', 'success');
            document.getElementById('api-keys-form').reset();
        } catch (error) {
            this.showAlert('Failed to save API keys', 'danger');
        }
    }

    // Bot creation
    async createBot() {
        const name = document.getElementById('bot-name').value;
        const templateId = document.getElementById('bot-template').value;
        const tokenId = document.getElementById('bot-discord-token').value;
        const geminiKey = document.getElementById('bot-gemini-key').value;

        if (!name || !templateId || !tokenId) {
            this.showAlert('Please fill in all required fields', 'warning');
            return;
        }

        // Find the actual token
        const token = this.tokens.find(t => t.id === tokenId);
        if (!token) {
            this.showAlert('Invalid Discord token selected', 'danger');
            return;
        }

        try {
            const response = await this.apiCall('/bots', {
                method: 'POST',
                body: JSON.stringify({
                    name,
                    template_id: templateId,
                    discord_token_id: tokenId, // Send the token ID
                    gemini_api_key: geminiKey || undefined
                })
            });

            this.showAlert('Bot created successfully', 'success');
            
            // Close modal and reset form
            const modal = bootstrap.Modal.getInstance(document.getElementById('createBotModal'));
            modal.hide();
            document.getElementById('create-bot-form').reset();
            
            this.loadBots();
        } catch (error) {
            this.showAlert('Failed to create bot', 'danger');
        }
    }

    // Monitoring functions
    async loadLogs() {
        try {
            const logs = await this.apiCall('/system/logs');
            this.renderLogs(logs.logs || []);
        } catch (error) {
            console.error('Failed to load logs:', error);
            document.getElementById('log-container').innerHTML = 
                '<p class="text-danger">Failed to load logs</p>';
        }
    }

    renderLogs(logs) {
        const container = document.getElementById('log-container');
        
        if (logs.length === 0) {
            container.innerHTML = '<p class="text-muted">No logs available</p>';
            return;
        }

        container.innerHTML = logs.map(log => `
            <div class="log-entry log-${log.level}">
                <span class="text-muted">[${log.timestamp}]</span>
                <span class="fw-bold">${log.level.toUpperCase()}:</span>
                ${log.message}
            </div>
        `).join('');
        
        // Auto-scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    // Utility functions
    formatUptime(lastHeartbeat) {
        if (!lastHeartbeat) return 'N/A';
        
        const now = Date.now() / 1000;
        const uptime = now - lastHeartbeat;
        
        if (uptime < 60) return '< 1m';
        if (uptime < 3600) return `${Math.floor(uptime / 60)}m`;
        if (uptime < 86400) return `${Math.floor(uptime / 3600)}h`;
        return `${Math.floor(uptime / 86400)}d`;
    }

    addActivityLog(message) {
        const container = document.getElementById('activity-log');
        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `
            <div>${message}</div>
            <div class="activity-time">${new Date().toLocaleTimeString()}</div>
        `;
        
        // Add to top
        if (container.firstChild && container.firstChild.textContent !== 'No recent activity') {
            container.insertBefore(item, container.firstChild);
        } else {
            container.innerHTML = '';
            container.appendChild(item);
        }
        
        // Keep only last 10 items
        while (container.children.length > 10) {
            container.removeChild(container.lastChild);
        }
    }

    showAlert(message, type = 'info') {
        // Create alert element
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }
}

// Global functions for onclick handlers
window.createBot = () => dashboard.createBot();
window.refreshDashboard = () => dashboard.refreshDashboard();
window.deleteToken = (id) => dashboard.deleteDiscordToken(id);

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new GrugThinkDashboard();
});