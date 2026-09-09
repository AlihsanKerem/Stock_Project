document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements - Tabs
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const trackedCount = document.getElementById('trackedCount');
    const alertsCount = document.getElementById('alertsCount');

    // DOM Elements - Tracked Stocks
    const trackedTableBody = document.getElementById('trackedTableBody');
    const addStockForm = document.getElementById('addStockForm');
    const newSymbolInput = document.getElementById('newSymbolInput');
    const marketType = document.getElementById('marketType');
    const addBtn = document.getElementById('addBtn');
    const messageBox = document.getElementById('messageBox');

    // DOM Elements - Alerts Table
    const alertsTableBody = document.getElementById('alertsTableBody');
    const openDirectAlertBtn = document.getElementById('openDirectAlertBtn');
    const refreshAlertsBtn = document.getElementById('refreshAlertsBtn');

    // DOM Elements - Alert Modal
    const alertModal = document.getElementById('alertModal');
    const closeAlertModalBtn = document.getElementById('closeAlertModalBtn');
    const cancelAlertBtn = document.getElementById('cancelAlertBtn');
    const alertForm = document.getElementById('alertForm');
    const alertSymbol = document.getElementById('alertSymbol');
    const alertRefPrice = document.getElementById('alertRefPrice');
    const alertTargetPct = document.getElementById('alertTargetPct');
    const alertNotes = document.getElementById('alertNotes');
    const fetchAlertRefPriceBtn = document.getElementById('fetchAlertRefPriceBtn');
    const alertPreviewBox = document.getElementById('alertPreviewBox');
    const alertPreviewPrice = document.getElementById('alertPreviewPrice');
    const quickPctButtons = document.querySelectorAll('.quick-pct-btn');

    let currentTracked = [];
    let currentAlerts = [];

    // Helper: Para birimi formatlama (₺)
    function formatCurrency(amount) {
        if (amount === undefined || amount === null || isNaN(amount)) return '₺0.00';
        return '₺' + Number(amount).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function showMessage(msg, isError = false) {
        messageBox.textContent = msg;
        messageBox.className = isError ? 'msg-error' : 'msg-success';
        messageBox.style.display = 'block';
        setTimeout(() => {
            messageBox.style.display = 'none';
        }, 5000);
    }

    // Tab Geçişleri
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');

            if (tabId === 'alertsTab') {
                loadAlerts();
            } else {
                loadTrackedStocks();
            }
        });
    });

    // ==================== 1. TAKİP EDİLEN HİSSELER ====================
    function loadTrackedStocks() {
        trackedTableBody.innerHTML = `
            <tr class="loading-row">
                <td colspan="4" style="text-align: center;">Takip listesi yükleniyor...</td>
            </tr>
        `;

        fetch('/api/tracked')
            .then(res => res.json())
            .then(result => {
                if (result.status === 'success') {
                    currentTracked = result.data;
                    trackedCount.textContent = result.data.length;
                    renderTrackedTable(result.data);
                } else {
                    trackedTableBody.innerHTML = `<tr><td colspan="4" style="color: var(--danger)">Hata: ${result.message}</td></tr>`;
                }
            })
            .catch(error => {
                console.error('Tracked fetch error:', error);
                trackedTableBody.innerHTML = `<tr><td colspan="4" style="color: var(--danger)">Bağlantı hatası oluştu.</td></tr>`;
            });
    }

    function renderTrackedTable(data) {
        trackedTableBody.innerHTML = '';

        if (!data || data.length === 0) {
            trackedTableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding: 2rem; color: var(--text-secondary);">Henüz takip ettiğiniz bir hisse bulunmuyor.</td></tr>`;
            return;
        }

        data.forEach((stock, index) => {
            const tr = document.createElement('tr');
            tr.style.animationDelay = `${index * 0.02}s`;
            
            const price = stock.last_price !== null ? formatCurrency(stock.last_price) : 'Bekleniyor...';
            const updatedAt = stock.updated_at ? new Date(stock.updated_at).toLocaleString('tr-TR') : '-';
            const cleanSymbol = stock.symbol.replace('.IS', '');

            tr.innerHTML = `
                <td>
                    <a href="/hisse-analiz?symbol=${cleanSymbol}" style="color: var(--accent); font-weight: 700; text-decoration: none;" title="Hisse Analizini Aç">
                        ${stock.symbol}
                    </a>
                </td>
                <td style="font-weight: 600;">${price}</td>
                <td style="color: var(--text-secondary); font-size: 0.9rem;">${updatedAt}</td>
                <td style="text-align: center; white-space: nowrap;">
                    <button class="btn-alarm set-alert-btn" data-symbol="${stock.symbol}" data-price="${stock.last_price || ''}" title="Bu hisseye fiyat alarmı kur">
                        ⏰ Alarm Kur
                    </button>
                    <button class="btn-danger remove-stock-btn" data-symbol="${stock.symbol}" title="Takip listesinden çıkar">
                        🗑️ Kaldır
                    </button>
                </td>
            `;
            trackedTableBody.appendChild(tr);
        });

        // Alarm Kur Butonları
        document.querySelectorAll('.set-alert-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sym = e.currentTarget.getAttribute('data-symbol');
                const lastPrice = e.currentTarget.getAttribute('data-price');
                openAlertModal(sym, lastPrice ? parseFloat(lastPrice) : null);
            });
        });

        // Kaldır Butonları
        document.querySelectorAll('.remove-stock-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const symbol = e.currentTarget.getAttribute('data-symbol');
                if (confirm(`${symbol} hissesini takipten çıkarmak istediğinize emin misiniz?`)) {
                    removeStock(symbol);
                }
            });
        });
    }

    addStockForm.addEventListener('submit', (e) => {
        e.preventDefault();
        let symbol = newSymbolInput.value.trim().toUpperCase();
        if (!symbol) return;
        
        const marketExt = marketType.value;
        if (marketExt !== 'CUSTOM' && !symbol.includes('.') && !symbol.includes('-')) {
            symbol = symbol + marketExt;
        }

        addBtn.disabled = true;
        addBtn.textContent = 'Ekleniyor...';

        fetch('/api/tracked/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol })
        })
        .then(res => res.json())
        .then(result => {
            addBtn.disabled = false;
            addBtn.textContent = '➕ Listeye Ekle';
            
            if (result.status === 'success') {
                showMessage(result.message);
                newSymbolInput.value = '';
                loadTrackedStocks();
            } else {
                showMessage(result.message, true);
            }
        })
        .catch(error => {
            addBtn.disabled = false;
            addBtn.textContent = '➕ Listeye Ekle';
            showMessage(`Bağlantı hatası: ${error}`, true);
        });
    });

    function removeStock(symbol) {
        fetch('/api/tracked/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol: symbol })
        })
        .then(res => res.json())
        .then(result => {
            if (result.status === 'success') {
                showMessage(result.message);
                loadTrackedStocks();
            } else {
                showMessage(result.message, true);
            }
        })
        .catch(error => {
            showMessage(`Bağlantı hatası: ${error}`, true);
        });
    }

    // ==================== 2. FİYAT ALARMLARI ====================
    function loadAlerts() {
        alertsTableBody.innerHTML = `
            <tr class="loading-row">
                <td colspan="9" style="text-align: center;">Alarmlar yükleniyor...</td>
            </tr>
        `;

        fetch('/api/alerts')
            .then(res => res.json())
            .then(result => {
                if (result.status === 'success') {
                    currentAlerts = result.data;
                    alertsCount.textContent = result.data.filter(a => a.status === 'ACTIVE').length;
                    renderAlertsTable(result.data);
                } else {
                    alertsTableBody.innerHTML = `<tr><td colspan="9" style="color: var(--danger)">Hata: ${result.message}</td></tr>`;
                }
            })
            .catch(err => {
                console.error('Alerts fetch error:', err);
                alertsTableBody.innerHTML = `<tr><td colspan="9" style="color: var(--danger)">Alarmlar yüklenirken hata oluştu.</td></tr>`;
            });
    }

    function renderAlertsTable(alerts) {
        alertsTableBody.innerHTML = '';

        if (!alerts || alerts.length === 0) {
            alertsTableBody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 2.5rem; color: var(--text-secondary);">
                        Henüz kurulmuş bir fiyat alarmı bulunmuyor.<br>
                        <span style="font-size: 0.9rem; color: var(--accent);">"Yeni Fiyat Alarmı Kur" butonuna tıklayarak ilk alarmınızı oluşturabilirsiniz.</span>
                    </td>
                </tr>
            `;
            return;
        }

        alerts.forEach(a => {
            const tr = document.createElement('tr');

            const isTriggered = a.status === 'TRIGGERED';
            const statusBadge = isTriggered 
                ? '<span class="badge-status badge-triggered">✓ Tetiklendi (Bildirildi)</span>' 
                : '<span class="badge-status badge-active">⏳ Aktif (İzleniyor)</span>';

            const dirEmoji = a.direction === 'UP' ? '📈 Yükseliş' : '📉 Düşüş';
            const dirColor = a.direction === 'UP' ? '#10b981' : '#ef4444';
            const pctSign = a.target_percentage >= 0 ? '+' : '';

            tr.innerHTML = `
                <td>
                    <span style="font-weight: 700; color: var(--accent);">${a.symbol}</span>
                </td>
                <td style="font-weight: 600;">${formatCurrency(a.reference_price)}</td>
                <td style="font-weight: 700; color: ${dirColor};">${pctSign}%${Number(a.target_percentage).toFixed(2)}</td>
                <td style="font-weight: 700;">${formatCurrency(a.target_price)}</td>
                <td><span style="color: ${dirColor}; font-weight: 600;">${dirEmoji}</span></td>
                <td>${statusBadge}</td>
                <td style="color: var(--text-secondary); font-size: 0.85rem;">${a.created_at ? a.created_at.split('.')[0] : '-'}</td>
                <td style="color: var(--text-secondary); font-size: 0.85rem;">${a.notes || '-'}</td>
                <td style="text-align: center;">
                    <button class="btn-danger delete-alert-btn" data-id="${a.id}" title="Alarmı Sil / İptal Et">
                        🗑️ İptal
                    </button>
                </td>
            `;
            alertsTableBody.appendChild(tr);
        });

        document.querySelectorAll('.delete-alert-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.getAttribute('data-id'));
                if (confirm('Bu alarmı iptal etmek / silmek istediğinize emin misiniz?')) {
                    deleteAlert(id);
                }
            });
        });
    }

    function deleteAlert(id) {
        fetch('/api/alerts/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id })
        })
        .then(res => res.json())
        .then(res => {
            if (res.status === 'success') {
                showMessage(res.message);
                loadAlerts();
            } else {
                showMessage(res.message, true);
            }
        })
        .catch(err => {
            console.error('Delete alert error:', err);
        });
    }

    refreshAlertsBtn.addEventListener('click', loadAlerts);

    // ==================== 3. ALARM KURMA MODALI ====================
    function openAlertModal(symbol = '', refPrice = null) {
        alertSymbol.value = symbol.replace('.IS', '');
        alertRefPrice.value = refPrice || '';
        alertTargetPct.value = '5.0'; // Default %5
        alertNotes.value = '';

        if (symbol && !refPrice) {
            fetchAlertRefPrice(symbol);
        } else {
            updateAlertPreview();
        }

        alertModal.classList.add('show');
    }

    openDirectAlertBtn.addEventListener('click', () => {
        openAlertModal();
    });

    closeAlertModalBtn.addEventListener('click', () => alertModal.classList.remove('show'));
    cancelAlertBtn.addEventListener('click', () => alertModal.classList.remove('show'));

    window.addEventListener('click', (e) => {
        if (e.target === alertModal) alertModal.classList.remove('show');
    });

    function updateAlertPreview() {
        const ref = parseFloat(alertRefPrice.value) || 0;
        const pct = parseFloat(alertTargetPct.value) || 0;

        if (ref > 0 && !isNaN(pct)) {
            const targetPrice = ref * (1 + pct / 100);
            const dirText = pct >= 0 ? 'Artış' : 'Düşüş';
            const sign = pct >= 0 ? '+' : '';
            const color = pct >= 0 ? '#10b981' : '#ef4444';

            alertPreviewPrice.style.color = color;
            alertPreviewPrice.textContent = `${formatCurrency(targetPrice)} (${sign}%${pct.toFixed(2)} ${dirText})`;
            alertPreviewBox.style.display = 'block';
        } else {
            alertPreviewBox.style.display = 'none';
        }
    }

    alertRefPrice.addEventListener('input', updateAlertPreview);
    alertTargetPct.addEventListener('input', updateAlertPreview);

    // Hızlı Yüzde Butonları
    quickPctButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const pct = btn.getAttribute('data-pct');
            alertTargetPct.value = pct;
            updateAlertPreview();
        });
    });

    async function fetchAlertRefPrice(sym) {
        if (!sym) sym = alertSymbol.value.trim().toUpperCase();
        if (!sym) return;

        fetchAlertRefPriceBtn.disabled = true;
        fetchAlertRefPriceBtn.textContent = '⏳ Çekiliyor...';

        try {
            const resp = await fetch(`/api/price/${encodeURIComponent(sym)}`);
            const res = await resp.json();

            if (res.status === 'success' && res.price) {
                alertRefPrice.value = res.price;
                updateAlertPreview();
            }
        } catch (err) {
            console.error('Fetch price error:', err);
        } finally {
            fetchAlertRefPriceBtn.disabled = false;
            fetchAlertRefPriceBtn.textContent = '⚡ Canlı Fiyatı Getir';
        }
    }

    fetchAlertRefPriceBtn.addEventListener('click', () => {
        fetchAlertRefPrice();
    });

    // Alarm Form Gönder
    alertForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        let sym = alertSymbol.value.trim().toUpperCase();
        if (!sym) return;

        const payload = {
            symbol: sym,
            reference_price: parseFloat(alertRefPrice.value),
            target_percentage: parseFloat(alertTargetPct.value),
            notes: alertNotes.value.trim()
        };

        try {
            const response = await fetch('/api/alerts/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const res = await response.json();

            if (res.status === 'success') {
                showMessage(res.message);
                alertModal.classList.remove('show');
                loadAlerts();
            } else {
                showMessage(res.message || 'Alarm kurulamadı.', true);
            }
        } catch (err) {
            console.error('Add alert error:', err);
            showMessage('Alarm kaydedilirken bağlantı hatası oluştu.', true);
        }
    });

    // Başlangıç Yüklemeleri
    loadTrackedStocks();
    loadAlerts();
});
