/**
 * 🤖 AI Agent Dashboard Widget & Chat Logic
 * BIST Otonom Portföy Asistanı Ön Yüz İstemcisi
 */

document.addEventListener('DOMContentLoaded', () => {
    initAgentWidget();
});

function initAgentWidget() {
    const drawer = document.getElementById('agentDrawer');
    const floatBtn = document.getElementById('agentFloatBtn');
    const closeBtn = document.getElementById('agentCloseBtn');
    const clearBtn = document.getElementById('agentClearBtn');
    const briefingBtn = document.getElementById('agentBriefingBtn');
    const chatInput = document.getElementById('agentChatInput');
    const sendBtn = document.getElementById('agentSendBtn');
    const chatBody = document.getElementById('agentChatBody');
    const quickChips = document.querySelectorAll('.agent-chip');

    if (!drawer || !floatBtn) return;

    let isHistoryLoaded = false;

    // Paneli Aç / Kapat
    floatBtn.addEventListener('click', () => {
        drawer.classList.add('open');
        if (!isHistoryLoaded) {
            loadChatHistory();
            isHistoryLoaded = true;
        }
        setTimeout(() => chatInput.focus(), 300);
    });

    closeBtn.addEventListener('click', () => {
        drawer.classList.remove('open');
    });

    // Sohbeti Temizle
    clearBtn.addEventListener('click', async () => {
        if (!confirm("Ajanla olan tüm sohbet geçmişini temizlemek istiyor musunuz?")) return;
        try {
            await fetch('/api/agent/clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: 'web_user' })
            });
            chatBody.innerHTML = '';
            appendWelcomeMessage();
        } catch (e) {
            console.error("Geçmiş temizleme hatası:", e);
        }
    });

    // Yönetici Özeti (Executive Briefing)
    briefingBtn.addEventListener('click', () => {
        handleSendMessage("Bana bugün için kapsamlı bir Yönetici Özeti ve Portföy Strateji Bülteni hazırla.");
    });

    // Hızlı İpuçları (Chips)
    quickChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const prompt = chip.getAttribute('data-prompt');
            if (prompt) {
                handleSendMessage(prompt);
            }
        });
    });

    // Mesaj Gönderme
    sendBtn.addEventListener('click', () => {
        const text = chatInput.value.trim();
        if (text) {
            handleSendMessage(text);
            chatInput.value = '';
        }
    });

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (text) {
                handleSendMessage(text);
                chatInput.value = '';
            }
        }
    });

    async function loadChatHistory() {
        try {
            const res = await fetch('/api/agent/history?session_id=web_user&limit=15');
            const data = await res.json();
            if (data.status === 'success' && data.history && data.history.length > 0) {
                chatBody.innerHTML = '';
                data.history.forEach(item => {
                    appendMessage(item.role, item.content, item.tool_calls);
                });
            } else {
                appendWelcomeMessage();
            }
        } catch (e) {
            console.error("Geçmiş yükleme hatası:", e);
            appendWelcomeMessage();
        }
    }

    function appendWelcomeMessage() {
        appendMessage('assistant', 
            "Merhaba! Ben BIST Otonom Portföy ve Risk Asistanınızım. 🤖\n\n" +
            "Portföy durumunuzu denetleyebilir, teknik sinyallerin 5 yıllık backtest başarılarını sorgulayabilir, " +
            "ATR Stop-Loss seviyelerinizi hesaplayabilir ve son haber duygu analizlerini sizin için sentezleyebilirim.\n\n" +
            "Aşağıdaki hızlı butonlardan birini seçebilir veya dilediğiniz soruyu sorabilirsiniz."
        );
    }

    async function handleSendMessage(text) {
        appendMessage('user', text);
        chatInput.value = '';
        chatInput.disabled = true;
        sendBtn.disabled = true;

        // Yükleniyor baloncuğu
        const loadingId = 'loading-' + Date.now();
        const loadingElem = document.createElement('div');
        loadingElem.id = loadingId;
        loadingElem.className = 'agent-msg assistant';
        loadingElem.innerHTML = `
            <div class="agent-msg-bubble" style="color: var(--accent);">
                <span style="display:inline-block; animation: pulse 1s infinite;">⏳ Veriler analiz ediliyor ve akıl yürütülüyor...</span>
            </div>
        `;
        chatBody.appendChild(loadingElem);
        chatBody.scrollTop = chatBody.scrollHeight;

        try {
            const res = await fetch('/api/agent/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, session_id: 'web_user' })
            });
            const data = await res.json();

            // Yükleniyor baloncuğunu kaldır
            const curLoading = document.getElementById(loadingId);
            if (curLoading) curLoading.remove();

            if (data.status === 'success') {
                appendMessage('assistant', data.response, data.thought_steps);
            } else {
                appendMessage('assistant', `⚠️ Hata: ${data.message || 'Yanıt alınamadı.'}`);
            }
        } catch (e) {
            const curLoading = document.getElementById(loadingId);
            if (curLoading) curLoading.remove();
            appendMessage('assistant', `⚠️ Bağlantı hatası: ${e.message}`);
        } finally {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    }

    function formatMarkdown(text) {
        if (!text) return '';
        let escaped = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Kalın metin **...**
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // İtalik metin *...*
        escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Kod `...`
        escaped = escaped.replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.1); padding: 2px 4px; border-radius: 4px;">$1</code>');
        // Satır sonları
        escaped = escaped.replace(/\n/g, '<br>');

        return escaped;
    }

    function appendMessage(role, content, toolCalls = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `agent-msg ${role}`;

        let toolTagsHtml = '';
        if (toolCalls && Array.isArray(toolCalls) && toolCalls.length > 0) {
            toolCalls.forEach(t => {
                const toolName = t.tool || (typeof t === 'string' ? t : 'araç');
                toolTagsHtml += `<div class="agent-tool-tag">⚡ ${toolName}</div>`;
            });
        }

        msgDiv.innerHTML = `
            ${toolTagsHtml}
            <div class="agent-msg-bubble">${formatMarkdown(content)}</div>
        `;

        chatBody.appendChild(msgDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }
}

