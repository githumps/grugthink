// GrugThink Dashboard JavaScript - Performance Optimized

class GrugThinkDashboard {
    constructor() {
        this.websocket = null;
        this.apiBase = '';
        this.bots = [];
        this.templates = {};
        this.tokens = [];
        this.loadingStates = new Set();
        this.updateQueue = new Map();
        this.lastLoadTimes = new Map();
        
        // Performance optimizations
        this.debounceTimeout = null;
        this.rafId = null;
        
        this.initTheme();
        this.bindEvents();
        this.loadInitialDataAsync();
    }
    
    // Optimized initial loading with lazy initialization
    async loadInitialDataAsync() {
        // Load critical data first
        await this.loadUser();
        
        // Delay WebSocket connection slightly to allow page to render
        setTimeout(() => this.initWebSocket(), 100);
        
        // Load dashboard data immediately for first tab
        await this.loadDashboard();
        
        // Lazy load other data only when needed
        this.lazyLoadRemaining();
    }
    
    // Lazy load non-critical data
    async lazyLoadRemaining() {
        // Use requestIdleCallback if available for better performance
        const loadFunc = async () => {
            await this.loadBots();
            await this.loadTemplates();
            await this.loadTokens();
        };
        
        if (window.requestIdleCallback) {
            window.requestIdleCallback(loadFunc, { timeout: 2000 });
        } else {
            setTimeout(loadFunc, 500);
        }
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
        // Debounce tab switching to prevent rapid API calls
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
        }
        
        this.debounceTimeout = setTimeout(() => {
            this.loadTabData(tabName);
        }, 150);
    }
    
    async loadTabData(tabName) {
        // Check if data is already loading
        if (this.loadingStates.has(tabName)) {
            return;
        }
        
        // Check cache validity (cache for 30 seconds)
        const lastLoad = this.lastLoadTimes.get(tabName);
        const now = Date.now();
        if (lastLoad && (now - lastLoad) < 30000) {
            return; // Use cached data
        }
        
        this.loadingStates.add(tabName);
        this.lastLoadTimes.set(tabName, now);
        
        try {
            switch (tabName) {
                case 'dashboard':
                    await this.loadDashboard();
                    break;
                case 'bots':
                    await this.loadBots();
                    break;
                case 'configuration':
                    await this.loadConfiguration();
                    break;
                case 'templates':
                    await this.loadTemplates();
                    break;
                case 'monitoring':
                    await this.loadLogs();
                    break;
            }
        } finally {
            this.loadingStates.delete(tabName);
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

    // Optimized API calls with caching and request deduplication
    async apiCall(endpoint, options = {}) {
        const cacheKey = `${endpoint}:${JSON.stringify(options)}`;
        
        // Check if request is already in flight
        if (this.updateQueue.has(cacheKey)) {
            return this.updateQueue.get(cacheKey);
        }
        
        const requestPromise = this._performApiCall(endpoint, options);
        this.updateQueue.set(cacheKey, requestPromise);
        
        try {
            const result = await requestPromise;
            return result;
        } finally {
            // Clean up after request completes
            this.updateQueue.delete(cacheKey);
        }
    }
    
    async _performApiCall(endpoint, options = {}) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
            
            const response = await fetch(`${this.apiBase}/api${endpoint}`, {
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                signal: controller.signal,
                ...options
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`API call failed: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                console.warn('API call timed out:', endpoint);
                this.showAlert('Request timed out. Please try again.', 'warning');
            } else {
                console.error('API call error:', error);
                this.showAlert('API call failed: ' + error.message, 'danger');
            }
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
        
        buttons.push(`<button class="btn btn-secondary btn-action" onclick="dashboard.editBot('${bot.bot_id}')" title="Edit Bot">
            <i class="bi bi-pencil"></i>
        </button>`);
        
        buttons.push(`<button class="btn btn-info btn-action" onclick="dashboard.viewBotLogs('${bot.bot_id}')" title="View Logs">
            <i class="bi bi-file-text"></i>
        </button>`);
        
        buttons.push(`<button class="btn btn-warning btn-action" onclick="dashboard.openMemoryManager('${bot.bot_id}', '${bot.name}')" title="Manage Memory">
            <i class="bi bi-memory"></i>
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

    async editBot(botId) {
        try {
            const bot = await this.apiCall(`/bots/${botId}`);
            this.showEditBotModal(bot);
        } catch (error) {
            this.showAlert('Failed to load bot details', 'danger');
        }
    }

    showEditBotModal(bot) {
        // Populate the edit modal with bot data
        document.getElementById('edit-bot-id').value = bot.bot_id;
        document.getElementById('edit-bot-name').value = bot.name;
        document.getElementById('edit-bot-personality').value = bot.personality || bot.force_personality || '';
        document.getElementById('edit-bot-load-embedder').checked = bot.load_embedder !== false;
        document.getElementById('edit-bot-log-level').value = bot.log_level || 'INFO';
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('editBotModal'));
        modal.show();
    }

    async saveEditBot() {
        try {
            const botId = document.getElementById('edit-bot-id').value;
            const personalityValue = document.getElementById('edit-bot-personality').value;
            const updates = {
                name: document.getElementById('edit-bot-name').value,
                personality: personalityValue,  // Use the new personality field
                force_personality: personalityValue,  // Keep for backward compatibility
                load_embedder: document.getElementById('edit-bot-load-embedder').checked,
                log_level: document.getElementById('edit-bot-log-level').value
            };

            await this.apiCall(`/bots/${botId}`, {
                method: 'PUT',
                body: JSON.stringify(updates)
            });

            this.showAlert('Bot updated successfully', 'success');
            this.loadBots();
            
            // Hide the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editBotModal'));
            modal.hide();
        } catch (error) {
            this.showAlert('Failed to update bot', 'danger');
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

            const personalityId = template.personality || template.force_personality;
            if (personalityId) {
                try {
                    const pres = await this.apiCall(`/personalities/${personalityId}`);
                    const yamlText = jsyaml.dump(pres.personality || {});
                    document.getElementById('edit-personality-yaml').value = yamlText;
                    document.getElementById('edit-personality-yaml').setAttribute('data-personality-id', personalityId);
                } catch (err) {
                    console.error('Failed to load personality', err);
                }
            }
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

                                <!-- Personality YAML -->
                                <h6 class="text-primary mb-3 mt-4">Personality YAML</h6>
                                <div class="mb-3">
                                    <textarea class="form-control font-monospace" id="edit-personality-yaml" rows="10"></textarea>
                                    <div class="form-text">Edit full personality definition</div>
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

        // Parse personality YAML and save
        const personalityField = document.getElementById('edit-personality-yaml');
        const personalityId = personalityField.getAttribute('data-personality-id');
        let personalityData = {};
        if (personalityField.value.trim()) {
            try {
                personalityData = jsyaml.load(personalityField.value);
            } catch (err) {
                this.showAlert('Invalid YAML in Personality definition', 'danger');
                return;
            }
        }
        
        try {
            if (personalityId && Object.keys(personalityData).length > 0) {
                await this.apiCall(`/personalities/${personalityId}`, {
                    method: 'PUT',
                    body: JSON.stringify(personalityData)
                });
            }

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
                            <div id="botLogsContainer" style="max-height: 400px; overflow-y: auto; background: var(--bg-secondary); padding: 15px; border-radius: 5px;"></div>
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
        
        container.innerHTML = logs.map(log => {
            const extraDetails = Object.entries(log)
                .filter(([k]) => !['level', 'message', 'timestamp', 'logger'].includes(k))
                .map(([k, v]) => `${k}: ${v}`)
                .join('<br>');

            return `
            <div class="log-entry log-${log.level} mb-2 p-2" style="border-left: 3px solid ${this.getLogColor(log.level)}; background: var(--card-bg);">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <span class="badge bg-${this.getLogBadgeColor(log.level)} me-2">${log.level.toUpperCase()}</span>
                        <small class="text-muted">${new Date(log.timestamp).toLocaleString()}</small>
                    </div>
                </div>
                <div class="mt-1">${log.message}</div>
                ${extraDetails ? `<pre class="p-2 mt-1 small" style="background: var(--bg-tertiary);">${extraDetails}</pre>` : ''}
                ${log.logger ? `<small class="text-muted">Logger: ${log.logger}</small>` : ''}
            </div>`;
        }).join('');
        
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

    // Dark mode theme management
    initTheme() {
        // Check for saved theme preference or default to light mode
        const savedTheme = localStorage.getItem('grugthink-theme') || 'light';
        this.setTheme(savedTheme);
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem('grugthink-theme', theme);
        
        // Update theme toggle button
        const themeIcon = document.getElementById('theme-icon');
        const themeText = document.getElementById('theme-text');
        
        if (theme === 'dark') {
            themeIcon.className = 'bi bi-sun-fill';
            themeText.textContent = 'Light';
        } else {
            themeIcon.className = 'bi bi-moon-fill';
            themeText.textContent = 'Dark';
        }
    }

    // AI Personality Generation functions
    async generatePersonality() {
        const personalityId = document.getElementById('personality-id').value.trim();
        const description = document.getElementById('personality-description').value.trim();
        
        if (!personalityId || !description) {
            this.showAlert('Please fill in both personality ID and description', 'warning');
            return;
        }
        
        // Validate personality ID format
        if (!/^[a-z_][a-z0-9_]*$/.test(personalityId)) {
            this.showAlert('Personality ID must start with a letter or underscore and contain only lowercase letters, numbers, and underscores', 'danger');
            return;
        }
        
        // Show progress and hide buttons
        document.getElementById('generation-progress').style.display = 'block';
        document.getElementById('generation-result').style.display = 'none';
        document.getElementById('generate-personality-btn').disabled = true;
        document.getElementById('save-personality-btn').style.display = 'none';
        
        try {
            const response = await this.apiCall('/personalities/generate', {
                method: 'POST',
                body: JSON.stringify({
                    personality_id: personalityId,
                    description: description
                })
            });
            
            // Show the generated YAML
            document.getElementById('generated-yaml').value = response.generated_yaml;
            document.getElementById('generation-result').style.display = 'block';
            document.getElementById('save-personality-btn').style.display = 'inline-block';
            document.getElementById('generate-personality-btn').textContent = 'Regenerate';
            
            // Store the response for saving
            this.generatedPersonalityData = response;
            
            this.showAlert('Personality generated successfully! Review and save when ready.', 'success');
            
        } catch (error) {
            console.error('Failed to generate personality:', error);
            this.showAlert('Failed to generate personality. Please try again.', 'danger');
        } finally {
            document.getElementById('generation-progress').style.display = 'none';
            document.getElementById('generate-personality-btn').disabled = false;
        }
    }
    
    async saveGeneratedPersonality() {
        if (!this.generatedPersonalityData) {
            this.showAlert('No personality data to save', 'danger');
            return;
        }
        
        try {
            // Store the personality ID before clearing the data
            const personalityId = this.generatedPersonalityData.personality_id;
            
            // Personality is already saved by the generation endpoint
            // Just close the modal and refresh
            const modal = bootstrap.Modal.getInstance(document.getElementById('createPersonalityModal'));
            modal.hide();
            
            // Reset the form
            document.getElementById('create-personality-form').reset();
            document.getElementById('generation-result').style.display = 'none';
            document.getElementById('save-personality-btn').style.display = 'none';
            document.getElementById('generate-personality-btn').textContent = 'Generate with AI';
            this.generatedPersonalityData = null;
            
            // Refresh templates to show updated personality options
            await this.loadTemplates();
            
            this.showAlert(`Personality '${personalityId}' saved successfully!`, 'success');
            
        } catch (error) {
            console.error('Failed to save personality:', error);
            this.showAlert('Failed to save personality', 'danger');
        }
    }

    // Memory Management Functions
    currentBotId = null;
    currentMemories = [];
    filteredMemories = [];
    memoryPage = 1;
    memoriesPerPage = 20;
    memorySearchQuery = '';

    async openMemoryManager(botId, botName) {
        this.currentBotId = botId;
        document.getElementById('memory-bot-name').textContent = botName;
        document.getElementById('memory-search').value = '';
        this.memorySearchQuery = '';
        this.memoryPage = 1;
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('memoryManagementModal'));
        modal.show();
        
        // Load memories
        await this.loadMemories();
    }

    async loadMemories() {
        try {
            // Show loading state
            document.getElementById('memory-list').innerHTML = `
                <div class="text-center py-3">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="mt-2 text-muted">Loading memories...</div>
                </div>
            `;
            
            const response = await this.apiCall(`/bots/${this.currentBotId}/memories?limit=1000`);
            this.currentMemories = response.memories || [];
            this.filteredMemories = [...this.currentMemories];
            
            this.updateMemoryDisplay();
            this.updateMemoryStats();
            
        } catch (error) {
            console.error('Failed to load memories:', error);
            document.getElementById('memory-list').innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    Failed to load memories: ${error.message}
                </div>
            `;
        }
    }

    searchMemories(query) {
        this.memorySearchQuery = query.toLowerCase();
        this.memoryPage = 1;
        
        if (!query.trim()) {
            this.filteredMemories = [...this.currentMemories];
        } else {
            this.filteredMemories = this.currentMemories.filter(memory => 
                memory.content.toLowerCase().includes(this.memorySearchQuery)
            );
        }
        
        this.updateMemoryDisplay();
        this.updateMemoryStats();
    }

    updateMemoryDisplay() {
        const startIndex = (this.memoryPage - 1) * this.memoriesPerPage;
        const endIndex = startIndex + this.memoriesPerPage;
        const pageMemories = this.filteredMemories.slice(startIndex, endIndex);
        
        const memoryList = document.getElementById('memory-list');
        
        if (pageMemories.length === 0) {
            memoryList.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-search text-muted" style="font-size: 2rem;"></i>
                    <div class="mt-2 text-muted">
                        ${this.memorySearchQuery ? 'No memories found matching your search.' : 'No memories found for this bot.'}
                    </div>
                </div>
            `;
            return;
        }
        
        const memoryItems = pageMemories.map((memory, index) => `
            <div class="card mb-2">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="memory-content">${this.escapeHtml(memory.content)}</div>
                            <div class="text-muted small mt-1">
                                ID: ${memory.id} | Added: ${new Date().toLocaleDateString()}
                            </div>
                        </div>
                        <div class="flex-shrink-0 ms-3">
                            <button class="btn btn-sm btn-outline-danger" 
                                    onclick="dashboard.deleteMemory('${this.escapeHtml(memory.content)}')"
                                    title="Delete Memory">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        memoryList.innerHTML = memoryItems;
        this.updateMemoryPagination();
    }

    updateMemoryStats() {
        document.getElementById('total-memories-count').textContent = this.currentMemories.length;
        document.getElementById('filtered-memories-count').textContent = this.filteredMemories.length;
    }

    updateMemoryPagination() {
        const totalPages = Math.ceil(this.filteredMemories.length / this.memoriesPerPage);
        const paginationInfo = document.getElementById('memory-pagination-info');
        const paginationNav = document.getElementById('memory-pagination');
        
        // Update pagination info
        const startIndex = (this.memoryPage - 1) * this.memoriesPerPage + 1;
        const endIndex = Math.min(this.memoryPage * this.memoriesPerPage, this.filteredMemories.length);
        paginationInfo.textContent = `Showing ${startIndex}-${endIndex} of ${this.filteredMemories.length} memories`;
        
        // Update pagination buttons
        if (totalPages <= 1) {
            paginationNav.innerHTML = '';
            return;
        }
        
        let paginationHTML = '';
        
        // Previous button
        paginationHTML += `
            <li class="page-item ${this.memoryPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="dashboard.changeMemoryPage(${this.memoryPage - 1})">Previous</a>
            </li>
        `;
        
        // Page numbers (show up to 5 pages)
        const startPage = Math.max(1, this.memoryPage - 2);
        const endPage = Math.min(totalPages, this.memoryPage + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <li class="page-item ${i === this.memoryPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="dashboard.changeMemoryPage(${i})">${i}</a>
                </li>
            `;
        }
        
        // Next button
        paginationHTML += `
            <li class="page-item ${this.memoryPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="dashboard.changeMemoryPage(${this.memoryPage + 1})">Next</a>
            </li>
        `;
        
        paginationNav.innerHTML = paginationHTML;
    }

    changeMemoryPage(page) {
        const totalPages = Math.ceil(this.filteredMemories.length / this.memoriesPerPage);
        if (page < 1 || page > totalPages) return;
        
        this.memoryPage = page;
        this.updateMemoryDisplay();
    }

    showAddMemoryForm() {
        document.getElementById('add-memory-form').style.display = 'block';
        document.getElementById('new-memory-content').focus();
    }

    hideAddMemoryForm() {
        document.getElementById('add-memory-form').style.display = 'none';
        document.getElementById('new-memory-content').value = '';
    }

    async addMemory() {
        const content = document.getElementById('new-memory-content').value.trim();
        
        if (!content) {
            this.showAlert('Please enter memory content', 'warning');
            return;
        }
        
        try {
            await this.apiCall(`/bots/${this.currentBotId}/memories`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            
            this.showAlert('Memory added successfully', 'success');
            this.hideAddMemoryForm();
            await this.loadMemories();
            
        } catch (error) {
            console.error('Failed to add memory:', error);
            this.showAlert(`Failed to add memory: ${error.message}`, 'danger');
        }
    }

    async deleteMemory(content) {
        if (!confirm('Are you sure you want to delete this memory? This action cannot be undone.')) {
            return;
        }
        
        try {
            await this.apiCall(`/bots/${this.currentBotId}/memories`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            
            this.showAlert('Memory deleted successfully', 'success');
            await this.loadMemories();
            
        } catch (error) {
            console.error('Failed to delete memory:', error);
            this.showAlert(`Failed to delete memory: ${error.message}`, 'danger');
        }
    }

    refreshMemories() {
        this.loadMemories();
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
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