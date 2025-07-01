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
            this.loadUser(),
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
                credentials: 'include', // Include session cookies
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

    // User functions
    async loadUser() {
        try {
            const user = await this.apiCall('/user');
            document.getElementById('username').textContent = user.username;
        } catch (error) {
            console.error('Failed to load user:', error);
            document.getElementById('username').textContent = 'Unknown';
        }
    }

    // Dashboard functions
    async loadDashboard() {
        try {
            const stats = await this.apiCall('/system/stats');
            
            document.getElementById('total-bots').textContent = stats.total_bots;
            document.getElementById('running-bots').textContent = stats.running_bots;
            document.getElementById('total-guilds').textContent = stats.total_guilds;
            
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
                    <span class="badge bg-secondary personality-badge">${bot.personality || bot.force_personality || 'adaptive'}</span>
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
        
        buttons.push(`<button class="btn btn-info btn-action" onclick="dashboard.viewBotLogs('${bot.bot_id}')" title="View Logs">
            <i class="bi bi-file-text"></i>
        </button>`);
        
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
            card.className = 'col-md-6 col-lg-4 mb-3';
            card.innerHTML = `
                <div class="card template-card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${template.name}</h5>
                        <p class="card-text">${template.description}</p>
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="badge bg-primary personality-badge">
                                ${template.personality || template.force_personality || 'adaptive'}
                            </span>
                            <small class="text-muted">
                                ${template.load_embedder ? 'ML Enabled' : 'Lightweight'}
                            </small>
                        </div>
                        <div class="d-flex justify-content-between">
                            <button class="btn btn-sm btn-primary" onclick="dashboard.selectTemplate('${id}')">
                                <i class="bi bi-plus-circle"></i> Use Template
                            </button>
                            <div>
                                <button class="btn btn-sm btn-outline-secondary me-1" onclick="dashboard.editTemplate('${id}')" title="Edit Template">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger" onclick="dashboard.deleteTemplate('${id}')" title="Delete Template">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
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
    
    async editTemplate(templateId) {
        try {
            const response = await this.apiCall(`/templates/${templateId}`);
            const template = response.template;
            this.showTemplateEditModal(templateId, template);
        } catch (error) {
            console.error('Failed to load template:', error);
            this.showAlert('Failed to load template for editing', 'danger');
        }
    }
    
    async deleteTemplate(templateId) {
        if (!confirm(`Are you sure you want to delete the template "${templateId}"?`)) {
            return;
        }
        
        try {
            await this.apiCall(`/templates/${templateId}`, { method: 'DELETE' });
            this.showAlert('Template deleted successfully', 'success');
            this.loadTemplates();
        } catch (error) {
            console.error('Failed to delete template:', error);
            this.showAlert('Failed to delete template', 'danger');
        }
    }
    
    showTemplateEditModal(templateId, template) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('editTemplateModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'editTemplateModal';
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Edit Template</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="edit-template-form">
                                <!-- Basic Template Info -->
                                <h6 class="text-primary mb-3">Basic Information</h6>
                                <div class="mb-3">
                                    <label for="edit-template-name" class="form-label">Template Name</label>
                                    <input type="text" class="form-control" id="edit-template-name" required>
                                </div>
                                <div class="mb-3">
                                    <label for="edit-template-description" class="form-label">Description</label>
                                    <textarea class="form-control" id="edit-template-description" rows="2" required></textarea>
                                </div>
                                
                                <!-- Personality Configuration -->
                                <h6 class="text-primary mb-3 mt-4">Personality Configuration</h6>
                                <div class="mb-3">
                                    <label for="edit-template-personality" class="form-label">Base Personality</label>
                                    <select class="form-select" id="edit-template-personality" required>
                                        <option value="grug">Grug (Caveman)</option>
                                        <option value="big_rob">Big Rob (Norf FC)</option>
                                        <option value="adaptive">Adaptive</option>
                                    </select>
                                </div>
                                
                                <!-- AI & ML Features -->
                                <h6 class="text-primary mb-3 mt-4">AI & ML Features</h6>
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="edit-template-embedder">
                                        <label class="form-check-label" for="edit-template-embedder">
                                            Load Embedder (Enable ML/Vector Search Features)
                                        </label>
                                        <div class="form-text">Enables semantic search and context understanding</div>
                                    </div>
                                </div>
                                
                                <!-- API Integrations -->
                                <h6 class="text-primary mb-3 mt-4">API Integrations</h6>
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="edit-template-gemini">
                                        <label class="form-check-label" for="edit-template-gemini">
                                            Default Gemini API Key
                                        </label>
                                        <div class="form-text">Use globally configured Gemini API key</div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="edit-template-ollama">
                                        <label class="form-check-label" for="edit-template-ollama">
                                            Default Ollama Integration
                                        </label>
                                        <div class="form-text">Use local Ollama models instead of Gemini</div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="edit-template-google-search">
                                        <label class="form-check-label" for="edit-template-google-search">
                                            Default Google Search
                                        </label>
                                        <div class="form-text">Enable internet search capabilities</div>
                                    </div>
                                </div>
                                
                                <!-- Advanced Configuration -->
                                <h6 class="text-primary mb-3 mt-4">Advanced Configuration</h6>
                                <div class="mb-3">
                                    <label for="edit-template-custom-env" class="form-label">Custom Environment Variables</label>
                                    <textarea class="form-control font-monospace" id="edit-template-custom-env" rows="4" placeholder='{"OLLAMA_URLS": "http://localhost:11434", "CUSTOM_SETTING": "value"}'></textarea>
                                    <div class="form-text">JSON format for custom environment variables</div>
                                </div>
                                
                                <!-- Log Level -->
                                <div class="mb-3">
                                    <label for="edit-template-log-level" class="form-label">Default Log Level</label>
                                    <select class="form-select" id="edit-template-log-level">
                                        <option value="DEBUG">DEBUG</option>
                                        <option value="INFO" selected>INFO</option>
                                        <option value="WARNING">WARNING</option>
                                        <option value="ERROR">ERROR</option>
                                    </select>
                                    <div class="form-text">Controls verbosity of bot logging</div>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" onclick="dashboard.saveTemplate()">Save Changes</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        // Populate form with template data
        document.getElementById('edit-template-name').value = template.name || '';
        document.getElementById('edit-template-description').value = template.description || '';
        document.getElementById('edit-template-personality').value = template.personality || 'adaptive';
        document.getElementById('edit-template-embedder').checked = template.load_embedder || false;
        document.getElementById('edit-template-gemini').checked = template.default_gemini_key || false;
        document.getElementById('edit-template-ollama').checked = template.default_ollama || false;
        document.getElementById('edit-template-google-search').checked = template.default_google_search || false;
        document.getElementById('edit-template-custom-env').value = JSON.stringify(template.custom_env || {}, null, 2);
        document.getElementById('edit-template-log-level').value = template.log_level || 'INFO';
        
        // Store the template ID for saving
        modal.setAttribute('data-template-id', templateId);
        
        // Show modal
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
    }
    
    async saveTemplate() {
        const modal = document.getElementById('editTemplateModal');
        const templateId = modal.getAttribute('data-template-id');
        
        // Parse custom environment variables
        let customEnv = {};
        try {
            const customEnvText = document.getElementById('edit-template-custom-env').value.trim();
            if (customEnvText) {
                customEnv = JSON.parse(customEnvText);
            }
        } catch (error) {
            this.showAlert('Invalid JSON in Custom Environment Variables', 'danger');
            return;
        }
        
        const templateData = {
            name: document.getElementById('edit-template-name').value,
            description: document.getElementById('edit-template-description').value,
            personality: document.getElementById('edit-template-personality').value,
            load_embedder: document.getElementById('edit-template-embedder').checked,
            default_gemini_key: document.getElementById('edit-template-gemini').checked,
            default_ollama: document.getElementById('edit-template-ollama').checked,
            default_google_search: document.getElementById('edit-template-google-search').checked,
            log_level: document.getElementById('edit-template-log-level').value,
            custom_env: customEnv
        };
        
        try {
            await this.apiCall(`/templates/${templateId}`, {
                method: 'PUT',
                body: JSON.stringify(templateData)
            });
            
            this.showAlert('Template updated successfully', 'success');
            
            // Close modal and refresh templates
            const bootstrapModal = bootstrap.Modal.getInstance(modal);
            bootstrapModal.hide();
            this.loadTemplates();
        } catch (error) {
            console.error('Failed to save template:', error);
            this.showAlert('Failed to save template', 'danger');
        }
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
    
    async viewBotLogs(botId) {
        try {
            const logs = await this.apiCall(`/bots/${botId}/logs`);
            this.showBotLogsModal(botId, logs.logs || []);
        } catch (error) {
            console.error('Failed to load bot logs:', error);
            this.showAlert('Failed to load bot logs', 'danger');
        }
    }
    
    showBotLogsModal(botId, logs) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('botLogsModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'botLogsModal';
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Bot Logs</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="botLogsContainer" style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 15px; border-radius: 5px;"></div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="dashboard.refreshBotLogs()">Refresh</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        // Update modal title and store current bot ID
        modal.querySelector('.modal-title').textContent = `Bot Logs - ${botId}`;
        this.currentLogBotId = botId;
        
        // Render logs
        this.renderBotLogs(logs);
        
        // Show modal - reuse existing modal instance to prevent overlay stacking
        let bootstrapModal = bootstrap.Modal.getInstance(modal);
        if (!bootstrapModal) {
            bootstrapModal = new bootstrap.Modal(modal);
        }
        bootstrapModal.show();
    }
    
    renderBotLogs(logs) {
        const container = document.getElementById('botLogsContainer');
        
        if (logs.length === 0) {
            container.innerHTML = '<p class="text-muted mb-0">No logs available for this bot</p>';
            return;
        }
        
        container.innerHTML = logs.map(log => `
            <div class="log-entry log-${log.level} mb-2 p-2" style="border-left: 3px solid ${this.getLogColor(log.level)}; background: white;">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <span class="badge bg-${this.getLogBadgeColor(log.level)} me-2">${log.level.toUpperCase()}</span>
                        <small class="text-muted">${new Date(log.timestamp).toLocaleString()}</small>
                    </div>
                </div>
                <div class="mt-1">${log.message}</div>
                ${log.logger ? `<small class="text-muted">Logger: ${log.logger}</small>` : ''}
            </div>
        `).join('');
        
        // Auto-scroll to bottom
        container.scrollTop = container.scrollHeight;
    }
    
    async refreshBotLogs() {
        if (this.currentLogBotId) {
            await this.viewBotLogs(this.currentLogBotId);
        }
    }
    
    getLogColor(level) {
        switch (level) {
            case 'error': return '#dc3545';
            case 'warning': return '#ffc107';
            case 'info': return '#0dcaf0';
            case 'debug': return '#6c757d';
            default: return '#6c757d';
        }
    }
    
    getLogBadgeColor(level) {
        switch (level) {
            case 'error': return 'danger';
            case 'warning': return 'warning';
            case 'info': return 'info';
            case 'debug': return 'secondary';
            default: return 'secondary';
        }
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