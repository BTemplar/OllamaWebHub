document.addEventListener('DOMContentLoaded', function () {
    const messagesContainer = document.getElementById('chat-messages');
    const form = document.getElementById('message-form');
    if (!form || !messagesContainer) return;

    const streamUrl = form.dataset.streamUrl;
    const username = form.dataset.username || 'You';
    const showReasoning = form.dataset.showReasoning === 'true';
    const textarea = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const stopButton = document.getElementById('stop-button');
    const expandToggle = document.getElementById('expand-toggle');
    const overlay = document.getElementById('overlay');
    const inputGroup = document.querySelector('.input-group');
    const fileInput = document.getElementById('fileInput');

    let abortController = null;
    let assistantState = null;
    let isStreaming = false;

    function getCsrfToken() {
        return form.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    function setStreamingState(active) {
        isStreaming = active;
        textarea.disabled = active;
        sendButton.style.display = active ? 'none' : '';
        stopButton.style.display = active ? '' : 'none';
        if (expandToggle) expandToggle.disabled = active;
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function formatTime(isoString) {
        const date = isoString ? new Date(isoString) : new Date();
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function renderMarkdown(text) {
        if (!text) return '';
        let html;
        if (typeof marked !== 'undefined') {
            html = marked.parse(text);
        } else {
            html = text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
        return `<div class="markdown-content">${html}</div>`;
    }

    function actionButtonsHtml(sender) {
        let html = '';
        if (sender === 'user') {
            html += '<button type="button" class="btn btn-outline-light btn-edit-message" title="Edit & regenerate"><i class="bi-pencil"></i></button>';
        }
        if (sender === 'user' || sender === 'assistant') {
            html += '<button type="button" class="btn btn-outline-light btn-regenerate-message" title="Regenerate"><i class="bi-arrow-clockwise"></i></button>';
        }
        return html;
    }

    function createMessageBubble(sender, label, messageId) {
        const wrapper = document.createElement('div');
        wrapper.className = `message-wrapper ${sender === 'user' ? 'user-message' : 'bot-message'} mb-3`;
        if (messageId) wrapper.dataset.messageId = messageId;
        wrapper.dataset.sender = sender;
        wrapper.innerHTML = `
            <div class="message-content p-3 rounded">
                <div class="d-flex justify-content-between align-items-start mb-2 gap-2">
                    <strong>${sender === 'user'
                        ? `<i class="bi-person me-2"></i>${label}`
                        : sender === 'system'
                            ? '<i class="bi-exclamation-triangle me-2"></i>System'
                            : '<i class="bi-robot me-2"></i>Assistant'}</strong>
                    <div class="d-flex align-items-center gap-2">
                        <div class="message-actions btn-group btn-group-sm">${actionButtonsHtml(sender)}</div>
                        <small class="text-muted message-time">today ${formatTime()}</small>
                    </div>
                </div>
                <div class="message-body">
                    <div class="message-text"></div>
                </div>
            </div>`;
        return wrapper;
    }

    function getPlainTextFromMessage(wrapper) {
        const markdown = wrapper.querySelector('.content-markdown');
        if (markdown) return markdown.innerText.trim();
        const textEl = wrapper.querySelector('.message-text');
        return textEl ? textEl.innerText.trim() : '';
    }

    function buildThinkSpoiler(thinkId, thinkingHtml, expanded) {
        const chevron = expanded ? 'bi-chevron-down' : 'bi-chevron-right';
        const collapseClass = expanded ? 'collapse show' : 'collapse';
        const spoiler = document.createElement('div');
        spoiler.className = 'think-spoiler mb-2';
        spoiler.innerHTML = `
            <a class="d-flex align-items-center spoiler-toggle text-decoration-none"
               data-bs-toggle="collapse"
               href="#${thinkId}"
               role="button"
               aria-expanded="${expanded ? 'true' : 'false'}">
                <i class="bi ${chevron} toggle-icon me-2" style="color: #0ddabb;"></i>
                <span class="small fw-medium" style="color: #0ddabb;">Show model reasoning</span>
            </a>
            <div class="${collapseClass} mt-1" id="${thinkId}">
                <div class="reasoning-content p-2 bg-info-subtle rounded">
                    <i class="bi bi-lightbulb me-2" style="color: #0D6EFD;"></i>
                    <div class="text-muted think-markdown">${thinkingHtml}</div>
                </div>
            </div>`;
        return spoiler;
    }

    function setMessageContent(wrapper, content, thinking) {
        const textEl = wrapper.querySelector('.message-text');
        let html = '';
        if (showReasoning && thinking) {
            const thinkId = `think-live-${Date.now()}`;
            const spoiler = buildThinkSpoiler(thinkId, renderMarkdown(thinking), false);
            html += spoiler.outerHTML;
        }
        html += `<div class="content-markdown">${renderMarkdown(content)}</div>`;
        textEl.innerHTML = html;
    }

    function appendUserMessage(data) {
        const bubble = createMessageBubble('user', username, data.id);
        if (data.image_url) {
            const img = document.createElement('img');
            img.src = data.image_url;
            img.className = 'message-thumbnail';
            img.alt = 'Uploaded image';
            bubble.querySelector('.message-content').insertBefore(
                img,
                bubble.querySelector('.d-flex')
            );
        }
        setMessageContent(bubble, data.content || '', '');
        if (data.timestamp) {
            bubble.querySelector('.message-time').textContent = `today ${formatTime(data.timestamp)}`;
        }
        messagesContainer.appendChild(bubble);
        scrollToBottom();
        return bubble;
    }

    function updateUserMessage(data) {
        const wrapper = messagesContainer.querySelector(`[data-message-id="${data.id}"]`);
        if (!wrapper) return appendUserMessage(data);
        setMessageContent(wrapper, data.content || '', '');
        if (data.timestamp) {
            wrapper.querySelector('.message-time').textContent = `today ${formatTime(data.timestamp)}`;
        }
        scrollToBottom();
    }

    function removeMessagesByIds(ids) {
        ids.forEach((id) => {
            const node = messagesContainer.querySelector(`[data-message-id="${id}"]`);
            if (node) node.remove();
        });
    }

    function createAssistantStreamBubble() {
        const bubble = createMessageBubble('assistant', 'Assistant');
        const textEl = bubble.querySelector('.message-text');
        textEl.classList.add('streaming', 'streaming-cursor');

        const thinkId = `think-live-${Date.now()}`;
        let thinkSpoiler = null;
        let thinkContent = null;
        if (showReasoning) {
            thinkSpoiler = buildThinkSpoiler(thinkId, '', true);
            thinkContent = thinkSpoiler.querySelector('.think-markdown');
            thinkSpoiler.style.display = 'none';
            textEl.appendChild(thinkSpoiler);
        }

        const contentEl = document.createElement('span');
        contentEl.className = 'content-live';
        textEl.appendChild(contentEl);

        messagesContainer.appendChild(bubble);
        scrollToBottom();

        return { bubble, textEl, contentEl, thinkSpoiler, thinkContent, content: '', thinking: '' };
    }

    function appendSystemMessage(message, messageId) {
        const bubble = createMessageBubble('system', 'System', messageId);
        bubble.querySelector('.message-text').textContent = message;
        messagesContainer.appendChild(bubble);
        scrollToBottom();
    }

    function finalizeAssistantStream(state, data) {
        state.content = data.content || state.content;
        state.thinking = data.thinking || state.thinking;
        state.textEl.classList.remove('streaming', 'streaming-cursor');
        if (data.message_id) state.bubble.dataset.messageId = data.message_id;
        state.bubble.dataset.sender = 'assistant';
        setMessageContent(state.bubble, state.content, state.thinking);
        if (data.timestamp) {
            state.bubble.querySelector('.message-time').textContent =
                `today ${formatTime(data.timestamp)}`;
        }
        scrollToBottom();
    }

    function finalizeStoppedStream(state) {
        if (!state || !state.content) {
            if (state?.bubble) state.bubble.remove();
            return;
        }
        state.textEl.classList.remove('streaming', 'streaming-cursor');
        state.content += '\n\n*[generation stopped]*';
        setMessageContent(state.bubble, state.content, state.thinking);
        scrollToBottom();
    }

    function parseSSEBlock(block) {
        const lines = block.split('\n');
        let eventType = 'message';
        const dataLines = [];
        for (const line of lines) {
            if (line.startsWith('event:')) eventType = line.slice(6).trim();
            else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
        }
        if (!dataLines.length) return null;
        return { type: eventType, data: JSON.parse(dataLines.join('\n')) };
    }

    async function consumeSSEStream(response, handlers) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const blocks = buffer.split('\n\n');
            buffer = blocks.pop() || '';
            for (const block of blocks) {
                if (!block.trim()) continue;
                const event = parseSSEBlock(block);
                if (event && handlers[event.type]) handlers[event.type](event.data);
            }
        }
    }

    async function runStream(formData) {
        abortController = new AbortController();
        assistantState = null;
        setStreamingState(true);

        try {
            const response = await fetch(streamUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData,
                signal: abortController.signal,
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            await consumeSSEStream(response, {
                truncated(data) {
                    removeMessagesByIds(data.removed_ids || []);
                },
                user_message(data) {
                    appendUserMessage(data);
                },
                message_updated(data) {
                    updateUserMessage(data);
                },
                generating() {
                    if (!assistantState) {
                        assistantState = createAssistantStreamBubble();
                        assistantState.contentEl.textContent = 'Generating response…';
                    }
                },
                chunk(data) {
                    if (!assistantState) assistantState = createAssistantStreamBubble();
                    if (data.type === 'content') {
                        assistantState.content += data.text;
                        assistantState.contentEl.textContent = assistantState.content;
                    } else if (data.type === 'thinking' && assistantState.thinkContent) {
                        assistantState.thinking += data.text;
                        assistantState.thinkSpoiler.style.display = '';
                        assistantState.thinkContent.innerHTML = renderMarkdown(assistantState.thinking);
                    }
                    scrollToBottom();
                },
                done(data) {
                    if (!assistantState) assistantState = createAssistantStreamBubble();
                    finalizeAssistantStream(assistantState, data);
                    assistantState = null;
                },
                error(data) {
                    appendSystemMessage(data.message || 'Something went wrong', data.message_id);
                    assistantState = null;
                },
            });
        } catch (error) {
            if (error.name === 'AbortError') {
                finalizeStoppedStream(assistantState);
                assistantState = null;
                return;
            }
            console.error('Stream error:', error);
            appendSystemMessage('Connection error. Please try again.');
        } finally {
            abortController = null;
            setStreamingState(false);
        }
    }

    async function handleSubmit(e) {
        e.preventDefault();
        if (isStreaming) return;

        const formData = new FormData(form);
        const message = (formData.get('message') || '').trim();
        const imageFile = formData.get('image');
        const hasImage = imageFile && imageFile.size > 0;
        if (!message && !hasImage) return;

        await runStream(formData);

        textarea.value = '';
        if (fileInput) {
            fileInput.value = '';
            const icon = fileInput.closest('.file-upload')?.querySelector('i');
            if (icon) icon.parentElement.classList.remove('file-selected');
        }
    }

    async function handleRegenerate(messageId) {
        if (isStreaming) return;
        const formData = new FormData();
        formData.append('regenerate_message_id', messageId);
        await runStream(formData);
    }

    async function handleEditSave(wrapper, newContent) {
        if (isStreaming || !newContent.trim()) return;
        const messageId = wrapper.dataset.messageId;
        const formData = new FormData();
        formData.append('edit_message_id', messageId);
        formData.append('message', newContent.trim());
        await runStream(formData);
    }

    function startEditMessage(wrapper) {
        if (isStreaming || wrapper.dataset.editing === 'true') return;
        wrapper.dataset.editing = 'true';
        const body = wrapper.querySelector('.message-body');
        const originalHtml = body.innerHTML;
        const currentText = getPlainTextFromMessage(wrapper);

        body.innerHTML = `
            <textarea class="form-control message-edit-area"></textarea>
            <div class="message-edit-actions">
                <button type="button" class="btn btn-sm btn-primary btn-save-edit">Save & regenerate</button>
                <button type="button" class="btn btn-sm btn-secondary btn-cancel-edit">Cancel</button>
            </div>`;

        const textareaEdit = body.querySelector('.message-edit-area');
        textareaEdit.value = currentText;
        textareaEdit.focus();

        body.querySelector('.btn-cancel-edit').addEventListener('click', () => {
            body.innerHTML = originalHtml;
            delete wrapper.dataset.editing;
        });

        body.querySelector('.btn-save-edit').addEventListener('click', async () => {
            const value = textareaEdit.value.trim();
            if (!value) return;
            body.innerHTML = originalHtml;
            delete wrapper.dataset.editing;
            await handleEditSave(wrapper, value);
        });
    }

    messagesContainer.addEventListener('click', (e) => {
        if (isStreaming) return;
        const wrapper = e.target.closest('.message-wrapper');
        if (!wrapper) return;
        if (e.target.closest('.btn-edit-message')) {
            startEditMessage(wrapper);
        } else if (e.target.closest('.btn-regenerate-message')) {
            handleRegenerate(wrapper.dataset.messageId);
        }
    });

    stopButton.addEventListener('click', () => {
        if (abortController) abortController.abort();
    });

    if (expandToggle && overlay) {
        expandToggle.addEventListener('click', () => {
            inputGroup.classList.toggle('expanded');
            overlay.style.display = inputGroup.classList.contains('expanded') ? 'block' : 'none';
            const icon = expandToggle.querySelector('i');
            icon.classList.toggle('bi-arrows-fullscreen');
            icon.classList.toggle('bi-fullscreen-exit');
        });
        overlay.addEventListener('click', () => expandToggle.click());
    }

    form.addEventListener('submit', handleSubmit);
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    });

    scrollToBottom();
});
