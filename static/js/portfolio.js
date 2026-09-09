document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements - KPI Summary
    const portfolioTableBody = document.getElementById('portfolioTableBody');
    const summaryTotalValue = document.getElementById('summaryTotalValue');
    const summaryTotalCost = document.getElementById('summaryTotalCost');
    const summaryTotalPnl = document.getElementById('summaryTotalPnl');
    const summaryTotalPnlPct = document.getElementById('summaryTotalPnlPct');
    const summaryPositionCount = document.getElementById('summaryPositionCount');
    const summaryTotalLots = document.getElementById('summaryTotalLots');
    const alertBox = document.getElementById('alertBox');
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');

    // Tab Elements
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const activePositionsTabCount = document.getElementById('activePositionsTabCount');
    const historyTabCount = document.getElementById('historyTabCount');
    const transactionsTableBody = document.getElementById('transactionsTableBody');

    // Monthly Target Elements
    const targetAmountDisplay = document.getElementById('targetAmountDisplay');
    const realizedPnlDisplay = document.getElementById('realizedPnlDisplay');
    const remainingTargetDisplay = document.getElementById('remainingTargetDisplay');
    const totalTradesDisplay = document.getElementById('totalTradesDisplay');
    const progressPctText = document.getElementById('progressPctText');
    const targetProgressBar = document.getElementById('targetProgressBar');
    const targetStatusText = document.getElementById('targetStatusText');
    const targetMonthText = document.getElementById('targetMonthText');
    const openTargetModalBtn = document.getElementById('openTargetModalBtn');

    // Target Modal Elements
    const targetModal = document.getElementById('targetModal');
    const closeTargetModalBtn = document.getElementById('closeTargetModalBtn');
    const cancelTargetBtn = document.getElementById('cancelTargetBtn');
    const targetForm = document.getElementById('targetForm');
    const targetInput = document.getElementById('targetInput');

    // Add Modal Elements
    const openAddModalBtn = document.getElementById('openAddModalBtn');
    const addModal = document.getElementById('addModal');
    const closeAddModalBtn = document.getElementById('closeAddModalBtn');
    const cancelAddBtn = document.getElementById('cancelAddBtn');
    const addPositionForm = document.getElementById('addPositionForm');
    const addMarket = document.getElementById('addMarket');
    const addSymbol = document.getElementById('addSymbol');
    const addLot = document.getElementById('addLot');
    const addBuyPrice = document.getElementById('addBuyPrice');
    const addNotes = document.getElementById('addNotes');
    const fetchAddPriceBtn = document.getElementById('fetchAddPriceBtn');
    const addPriceStatus = document.getElementById('addPriceStatus');

    // Edit Modal Elements
    const editModal = document.getElementById('editModal');
    const closeEditModalBtn = document.getElementById('closeEditModalBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    const editPositionForm = document.getElementById('editPositionForm');
    const editPositionId = document.getElementById('editPositionId');
    const editSymbol = document.getElementById('editSymbol');
    const editLot = document.getElementById('editLot');
    const editBuyPrice = document.getElementById('editBuyPrice');
    const editNotes = document.getElementById('editNotes');
    const fetchEditPriceBtn = document.getElementById('fetchEditPriceBtn');
    const editPriceStatus = document.getElementById('editPriceStatus');

    // Sell Modal Elements
    const sellModal = document.getElementById('sellModal');
    const closeSellModalBtn = document.getElementById('closeSellModalBtn');
    const cancelSellBtn = document.getElementById('cancelSellBtn');
    const sellPositionForm = document.getElementById('sellPositionForm');
    const sellPositionId = document.getElementById('sellPositionId');
    const sellBuyPrice = document.getElementById('sellBuyPrice');
    const sellMaxLot = document.getElementById('sellMaxLot');
    const sellLot = document.getElementById('sellLot');
    const sellPrice = document.getElementById('sellPrice');
    const sellNotes = document.getElementById('sellNotes');
    const sellInfoBox = document.getElementById('sellInfoBox');
    const sellPreviewBox = document.getElementById('sellPreviewBox');
    const sellPreviewPnl = document.getElementById('sellPreviewPnl');
    const fetchSellPriceBtn = document.getElementById('fetchSellPriceBtn');
    const sellPriceStatus = document.getElementById('sellPriceStatus');

    let currentPositions = [];
    let currentTransactions = [];
    let currentTargetStats = null;

    // Helper: Para birimi formatlama (₺)
    function formatCurrency(amount) {
        if (amount === undefined || amount === null || isNaN(amount)) return '₺0.00';
        return '₺' + Number(amount).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // Helper: Yüzde formatlama (%)
    function formatPercent(val) {
        if (val === undefined || val === null || isNaN(val)) return '%0.00';
        const sign = val > 0 ? '+' : '';
        return `${sign}%${Number(val).toFixed(2)}`;
    }

    // Mesaj kutusu gösterme
    function showAlert(message, type = 'success') {
        alertBox.textContent = message;
        alertBox.className = type === 'success' ? 'msg-success' : 'msg-error';
        alertBox.style.display = 'block';
        setTimeout(() => {
            alertBox.style.display = 'none';
        }, 5000);
    }

    // Tab Değiştirme
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');

            if (tabId === 'historyTab') {
                loadTransactions();
            }
        });
    });

    // ==================== 1. HEDEF VERİLERİNİ ÇEK VE GÜNCELLE ====================
    async function loadTargetStats() {
        try {
            const resp = await fetch('/api/target/stats');
            const res = await resp.json();

            if (res.status === 'success') {
                currentTargetStats = res.data;
                renderTargetStats(res.data);
            }
        } catch (err) {
            console.error('Target stats error:', err);
        }
    }

    function renderTargetStats(stats) {
        targetAmountDisplay.textContent = formatCurrency(stats.monthly_target);
        realizedPnlDisplay.textContent = formatCurrency(stats.realized_pnl);
        remainingTargetDisplay.textContent = formatCurrency(stats.remaining_tl);
        totalTradesDisplay.textContent = `${stats.total_trades} İşlem`;

        if (stats.year_month) {
            const [y, m] = stats.year_month.split('-');
            const dateObj = new Date(parseInt(y), parseInt(m) - 1, 1);
            const monthName = dateObj.toLocaleString('tr-TR', { month: 'long', year: 'numeric' });
            targetMonthText.textContent = monthName.charAt(0).toUpperCase() + monthName.slice(1);
        }

        // Renklendirme
        if (stats.realized_pnl > 0) {
            realizedPnlDisplay.className = 'target-stat-val text-success';
        } else if (stats.realized_pnl < 0) {
            realizedPnlDisplay.className = 'target-stat-val text-danger';
        } else {
            realizedPnlDisplay.className = 'target-stat-val text-neutral';
        }

        // Progress Bar
        const pct = stats.progress_pct || 0;
        progressPctText.textContent = `%${pct.toFixed(2)}`;

        if (stats.monthly_target <= 0) {
            targetProgressBar.style.width = '0%';
            targetStatusText.textContent = 'Aylık hedef belirlemek için "Hedefi Değiştir"e tıklayın.';
        } else if (stats.realized_pnl < 0) {
            targetProgressBar.className = 'progress-bar-fill negative';
            targetProgressBar.style.width = '100%';
            targetStatusText.textContent = 'Bu ay henüz zarardasınız, hedefe doğru ilerleyin!';
        } else if (pct >= 100) {
            targetProgressBar.className = 'progress-bar-fill';
            targetProgressBar.style.width = '100%';
            targetStatusText.textContent = '🎉 Tebrikler! Bu ayki kazanç hedefinize ulaştınız!';
        } else {
            targetProgressBar.className = 'progress-bar-fill';
            targetProgressBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
            targetStatusText.textContent = `Hedefe ulaşmaya ${formatCurrency(stats.remaining_tl)} kaldı.`;
        }
    }

    // ==================== 2. AKTİF PORTFÖYÜ ÇEK VE LİSTELE ====================
    async function loadPortfolio() {
        portfolioTableBody.innerHTML = `
            <tr class="loading-row">
                <td colspan="10" style="text-align: center;">Portföy verileri ve canlı fiyatlar çekiliyor...</td>
            </tr>
        `;

        try {
            const response = await fetch('/api/portfolio');
            const res = await response.json();

            if (res.status === 'success') {
                renderSummary(res.data.summary);
                renderTable(res.data.positions);
                currentPositions = res.data.positions;
                activePositionsTabCount.textContent = res.data.positions.length;
            } else {
                showAlert(res.message || 'Veriler yüklenirken hata oluştu.', 'error');
            }
        } catch (error) {
            console.error('Portfolio fetch error:', error);
            showAlert('Sunucuya bağlanılamadı.', 'error');
        }
    }

    function renderSummary(summary) {
        summaryTotalValue.textContent = formatCurrency(summary.total_value);
        summaryTotalCost.textContent = formatCurrency(summary.total_cost);
        summaryTotalPnl.textContent = formatCurrency(summary.total_pnl);
        summaryTotalPnlPct.textContent = formatPercent(summary.total_pnl_pct);

        summaryPositionCount.textContent = `${summary.position_count} Farklı Pozisyon`;
        summaryTotalLots.textContent = `${summary.total_lots.toLocaleString('tr-TR')} Toplam Lot`;

        if (summary.total_pnl > 0) {
            summaryTotalPnl.className = 'summary-value text-success';
            summaryTotalPnlPct.className = 'summary-subtext text-success';
        } else if (summary.total_pnl < 0) {
            summaryTotalPnl.className = 'summary-value text-danger';
            summaryTotalPnlPct.className = 'summary-subtext text-danger';
        } else {
            summaryTotalPnl.className = 'summary-value text-neutral';
            summaryTotalPnlPct.className = 'summary-subtext text-neutral';
        }
    }

    function renderTable(positions) {
        if (!positions || positions.length === 0) {
            portfolioTableBody.innerHTML = `
                <tr>
                    <td colspan="10">
                        <div class="empty-portfolio">
                            <span>💼</span>
                            <p>Henüz portföyünüzde kayıtlı açık bir hisse senedi bulunmuyor.</p>
                            <p style="font-size: 0.9rem; margin-top: 0.5rem; color: var(--accent);">"Yeni Hisse / Lot Ekle" butonuna tıklayarak ilk pozisyonunuzu ekleyebilirsiniz.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        portfolioTableBody.innerHTML = '';
        positions.forEach(pos => {
            const tr = document.createElement('tr');

            const pnlClass = pos.pnl > 0 ? 'text-success' : pos.pnl < 0 ? 'text-danger' : 'text-neutral';
            const badgeClass = pos.pnl > 0 ? 'positive' : pos.pnl < 0 ? 'negative' : 'neutral';
            const cleanSymbol = pos.symbol.replace('.IS', '');
            const dateStr = pos.buy_date ? pos.buy_date.split(' ')[0] : '-';

            tr.innerHTML = `
                <td>
                    <a href="/hisse-analiz?symbol=${cleanSymbol}" style="color: var(--accent); font-weight: 700; text-decoration: none;" title="Hisse Analizini Aç">
                        ${pos.symbol}
                    </a>
                </td>
                <td style="font-weight: 600;">${pos.lot.toLocaleString('tr-TR')}</td>
                <td>${formatCurrency(pos.buy_price)}</td>
                <td style="font-weight: 600;">${formatCurrency(pos.current_price)}</td>
                <td>${formatCurrency(pos.total_cost)}</td>
                <td style="font-weight: 600;">${formatCurrency(pos.current_value)}</td>
                <td class="${pnlClass}" style="font-weight: 700;">${formatCurrency(pos.pnl)}</td>
                <td>
                    <span class="pnl-badge ${badgeClass}">${formatPercent(pos.pnl_pct)}</span>
                </td>
                <td style="color: var(--text-secondary); font-size: 0.85rem;" title="${pos.notes || ''}">
                    ${dateStr}
                    ${pos.notes ? ` <span title="${pos.notes}" style="cursor:help;">💬</span>` : ''}
                </td>
                <td style="text-align: center; white-space: nowrap;">
                    <button class="btn-sell sell-btn" data-id="${pos.id}" title="Hisse Satışı Yap">💵 Sat</button>
                    <button class="action-btn edit-btn" data-id="${pos.id}" title="Düzenle">✏️</button>
                    <button class="action-btn delete delete-btn" data-id="${pos.id}" data-symbol="${pos.symbol}" title="Sil">🗑️</button>
                </td>
            `;
            portfolioTableBody.appendChild(tr);
        });

        // Event listener'ları bağla
        document.querySelectorAll('.sell-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.getAttribute('data-id'));
                const pos = currentPositions.find(p => p.id === id);
                if (pos) openSellModal(pos);
            });
        });

        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.getAttribute('data-id'));
                const pos = currentPositions.find(p => p.id === id);
                if (pos) openEditModal(pos);
            });
        });

        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = parseInt(e.currentTarget.getAttribute('data-id'));
                const symbol = e.currentTarget.getAttribute('data-symbol');
                if (confirm(`${symbol} pozisyonunu portföyden silmek istediğinize emin misiniz?`)) {
                    await deletePosition(id);
                }
            });
        });
    }

    // ==================== 3. SATIŞ GEÇMİŞİNİ ÇEK VE LİSTELE ====================
    async function loadTransactions() {
        transactionsTableBody.innerHTML = `
            <tr class="loading-row">
                <td colspan="10" style="text-align: center;">Satış geçmişi yükleniyor...</td>
            </tr>
        `;

        try {
            const response = await fetch('/api/transactions');
            const res = await response.json();

            if (res.status === 'success') {
                currentTransactions = res.data;
                historyTabCount.textContent = res.data.length;
                renderTransactions(res.data);
            }
        } catch (err) {
            console.error('Transactions fetch error:', err);
            transactionsTableBody.innerHTML = `
                <tr><td colspan="10" style="text-align: center; color: var(--danger);">Geçmiş yüklenirken hata oluştu.</td></tr>
            `;
        }
    }

    function renderTransactions(txs) {
        if (!txs || txs.length === 0) {
            transactionsTableBody.innerHTML = `
                <tr>
                    <td colspan="10">
                        <div class="empty-portfolio">
                            <span>📜</span>
                            <p>Henüz gerçekleştirilmiş bir satış işlemi kaydı bulunmuyor.</p>
                            <p style="font-size: 0.9rem; margin-top: 0.5rem; color: var(--accent);">Portföyünüzdeki hisseleri sattığınızda kazançlarınız burada listelenecektir.</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        transactionsTableBody.innerHTML = '';
        txs.forEach(tx => {
            const tr = document.createElement('tr');
            const pnlClass = tx.realized_pnl > 0 ? 'text-success' : tx.realized_pnl < 0 ? 'text-danger' : 'text-neutral';
            const badgeClass = tx.realized_pnl > 0 ? 'positive' : tx.realized_pnl < 0 ? 'negative' : 'neutral';
            const totalRevenue = tx.lot * tx.sell_price;

            tr.innerHTML = `
                <td style="color: var(--text-secondary); font-size: 0.9rem;">${tx.sell_date ? tx.sell_date.split('.')[0] : '-'}</td>
                <td>
                    <span style="color: var(--accent); font-weight: 700;">${tx.symbol}</span>
                </td>
                <td style="font-weight: 600;">${tx.lot.toLocaleString('tr-TR')}</td>
                <td>${formatCurrency(tx.buy_price)}</td>
                <td style="font-weight: 600;">${formatCurrency(tx.sell_price)}</td>
                <td style="font-weight: 600;">${formatCurrency(totalRevenue)}</td>
                <td class="${pnlClass}" style="font-weight: 700;">${formatCurrency(tx.realized_pnl)}</td>
                <td>
                    <span class="pnl-badge ${badgeClass}">${formatPercent(tx.realized_pnl_pct)}</span>
                </td>
                <td style="color: var(--text-secondary); font-size: 0.85rem;">${tx.notes || '-'}</td>
                <td style="text-align: center;">
                    <button class="action-btn delete delete-tx-btn" data-id="${tx.id}" title="Kaydı Sil">🗑️</button>
                </td>
            `;
            transactionsTableBody.appendChild(tr);
        });

        document.querySelectorAll('.delete-tx-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = parseInt(e.currentTarget.getAttribute('data-id'));
                if (confirm('Bu satış kaydını silmek istediğinize emin misiniz?')) {
                    await deleteTransaction(id);
                }
            });
        });
    }

    async function deleteTransaction(id) {
        try {
            const resp = await fetch('/api/transactions/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            });
            const res = await resp.json();
            if (res.status === 'success') {
                showAlert(res.message, 'success');
                loadTransactions();
                loadTargetStats();
            } else {
                showAlert(res.message || 'Silme başarısız.', 'error');
            }
        } catch (err) {
            console.error('Delete tx error:', err);
        }
    }

    // ==================== 4. SATIŞ YAP (SELL MODAL) MANTIĞI ====================
    function openSellModal(pos) {
        sellPositionId.value = pos.id;
        sellBuyPrice.value = pos.buy_price;
        sellMaxLot.value = pos.lot;
        sellLot.value = pos.lot;
        sellLot.max = pos.lot;
        sellPrice.value = pos.current_price || pos.buy_price;
        sellNotes.value = '';
        sellPriceStatus.style.display = 'none';

        sellInfoBox.innerHTML = `
            <strong>${pos.symbol}</strong> satışı yapılıyor.<br>
            <span style="font-size: 0.85rem; color: var(--text-secondary);">
                Mevcut Lot: <b>${pos.lot}</b> | Alış Maliyeti: <b>${formatCurrency(pos.buy_price)}</b> | Güncel Piyasa: <b>${formatCurrency(pos.current_price)}</b>
            </span>
        `;

        updateSellPreview();
        sellModal.classList.add('show');
    }

    function updateSellPreview() {
        const lot = parseInt(sellLot.value) || 0;
        const sPrice = parseFloat(sellPrice.value) || 0;
        const bPrice = parseFloat(sellBuyPrice.value) || 0;

        if (lot > 0 && sPrice > 0 && bPrice > 0) {
            const pnl = (sPrice - bPrice) * lot;
            const pct = ((sPrice - bPrice) / bPrice) * 100;
            const pnlSign = pnl >= 0 ? '+' : '';
            const colorClass = pnl >= 0 ? '#10b981' : '#ef4444';

            sellPreviewPnl.style.color = colorClass;
            sellPreviewPnl.textContent = `${pnlSign}${formatCurrency(pnl)} (${pnlSign}%${pct.toFixed(2)})`;
            sellPreviewBox.style.display = 'block';
        } else {
            sellPreviewBox.style.display = 'none';
        }
    }

    sellLot.addEventListener('input', updateSellPreview);
    sellPrice.addEventListener('input', updateSellPreview);

    fetchSellPriceBtn.addEventListener('click', async () => {
        const id = parseInt(sellPositionId.value);
        const pos = currentPositions.find(p => p.id === id);
        if (!pos) return;

        fetchSellPriceBtn.disabled = true;
        fetchSellPriceBtn.textContent = '⏳ Çekiliyor...';

        try {
            const resp = await fetch(`/api/price/${encodeURIComponent(pos.symbol)}`);
            const res = await resp.json();

            if (res.status === 'success' && res.price) {
                sellPrice.value = res.price;
                sellPriceStatus.style.display = 'block';
                sellPriceStatus.style.color = '#10b981';
                sellPriceStatus.textContent = `✓ Güncel Fiyat: ₺${res.price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`;
                updateSellPreview();
            }
        } catch (err) {
            console.error('Fetch sell price error:', err);
        } finally {
            fetchSellPriceBtn.disabled = false;
            fetchSellPriceBtn.textContent = '⚡ Güncel Fiyattan Sat';
        }
    });

    sellPositionForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            position_id: parseInt(sellPositionId.value),
            lot: parseInt(sellLot.value),
            sell_price: parseFloat(sellPrice.value),
            notes: sellNotes.value.trim()
        };

        try {
            const response = await fetch('/api/portfolio/sell', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const res = await response.json();

            if (res.status === 'success') {
                showAlert(res.message, 'success');
                sellModal.classList.remove('show');
                loadPortfolio();
                loadTargetStats();
                loadTransactions();
            } else {
                showAlert(res.message || 'Satış işlemi başarısız.', 'error');
            }
        } catch (err) {
            console.error('Sell error:', err);
            showAlert('Satış yapılırken sunucu hatası oluştu.', 'error');
        }
    });

    closeSellModalBtn.addEventListener('click', () => sellModal.classList.remove('show'));
    cancelSellBtn.addEventListener('click', () => sellModal.classList.remove('show'));

    // ==================== 5. AYLIK HEDEF AYARLAMA MODALI ====================
    openTargetModalBtn.addEventListener('click', () => {
        if (currentTargetStats) {
            targetInput.value = currentTargetStats.monthly_target || '';
        }
        targetModal.classList.add('show');
    });

    closeTargetModalBtn.addEventListener('click', () => targetModal.classList.remove('show'));
    cancelTargetBtn.addEventListener('click', () => targetModal.classList.remove('show'));

    targetForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const targetVal = parseFloat(targetInput.value);
        if (isNaN(targetVal) || targetVal < 0) {
            showAlert('Lütfen geçerli bir hedef tutarı giriniz.', 'error');
            return;
        }

        try {
            const resp = await fetch('/api/target/set', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_tl: targetVal })
            });
            const res = await resp.json();

            if (res.status === 'success') {
                showAlert(res.message, 'success');
                targetModal.classList.remove('show');
                loadTargetStats();
            } else {
                showAlert(res.message || 'Hedef kaydedilemedi.', 'error');
            }
        } catch (err) {
            console.error('Set target error:', err);
            showAlert('Sunucu hatası.', 'error');
        }
    });

    // ==================== 6. POZİSYON SİLME / EKLEME / DÜZENLEME ====================
    async function deletePosition(id) {
        try {
            const response = await fetch('/api/portfolio/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            });
            const res = await response.json();
            if (res.status === 'success') {
                showAlert(res.message, 'success');
                loadPortfolio();
            } else {
                showAlert(res.message || 'Silme işlemi başarısız.', 'error');
            }
        } catch (error) {
            console.error('Delete error:', error);
            showAlert('Sunucu hatası.', 'error');
        }
    }

    openAddModalBtn.addEventListener('click', () => {
        addPositionForm.reset();
        addPriceStatus.style.display = 'none';
        addModal.classList.add('show');
    });

    closeAddModalBtn.addEventListener('click', () => addModal.classList.remove('show'));
    cancelAddBtn.addEventListener('click', () => addModal.classList.remove('show'));

    closeEditModalBtn.addEventListener('click', () => editModal.classList.remove('show'));
    cancelEditBtn.addEventListener('click', () => editModal.classList.remove('show'));

    window.addEventListener('click', (e) => {
        if (e.target === addModal) addModal.classList.remove('show');
        if (e.target === editModal) editModal.classList.remove('show');
        if (e.target === sellModal) sellModal.classList.remove('show');
        if (e.target === targetModal) targetModal.classList.remove('show');
    });

    // Güncel Fiyat Çekme (Ekleme Modalı)
    fetchAddPriceBtn.addEventListener('click', async () => {
        let symbol = addSymbol.value.trim().toUpperCase();
        const market = addMarket.value;

        if (!symbol) {
            addPriceStatus.style.display = 'block';
            addPriceStatus.style.color = '#f59e0b';
            addPriceStatus.textContent = '⚠️ Lütfen önce bir hisse kodu giriniz.';
            return;
        }

        if (market === '.IS' && !symbol.endsWith('.IS')) {
            symbol = symbol + '.IS';
        } else if (market === '-USD' && !symbol.endsWith('-USD')) {
            symbol = symbol + '-USD';
        }

        fetchAddPriceBtn.disabled = true;
        fetchAddPriceBtn.textContent = '⏳ Çekiliyor...';
        addPriceStatus.style.display = 'block';
        addPriceStatus.style.color = 'var(--text-secondary)';
        addPriceStatus.textContent = 'Canlı piyasa fiyatı sorgulanıyor...';

        try {
            const resp = await fetch(`/api/price/${encodeURIComponent(symbol)}`);
            const res = await resp.json();

            if (res.status === 'success' && res.price) {
                addBuyPrice.value = res.price;
                addPriceStatus.style.color = '#10b981';
                addPriceStatus.textContent = `✓ Güncel Fiyat: ₺${res.price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`;
            } else {
                addPriceStatus.style.color = '#ef4444';
                addPriceStatus.textContent = res.message || 'Fiyat bilgisi alınamadı.';
            }
        } catch (err) {
            console.error('Fetch price error:', err);
            addPriceStatus.style.color = '#ef4444';
            addPriceStatus.textContent = 'Fiyat çekilirken ağ hatası oluştu.';
        } finally {
            fetchAddPriceBtn.disabled = false;
            fetchAddPriceBtn.textContent = '⚡ Güncel Fiyattan Al';
        }
    });

    // Güncel Fiyat Çekme (Düzenleme Modalı)
    fetchEditPriceBtn.addEventListener('click', async () => {
        const symbol = editSymbol.value.trim().toUpperCase();
        if (!symbol) return;

        fetchEditPriceBtn.disabled = true;
        fetchEditPriceBtn.textContent = '⏳ Çekiliyor...';
        editPriceStatus.style.display = 'block';
        editPriceStatus.style.color = 'var(--text-secondary)';
        editPriceStatus.textContent = 'Canlı fiyat sorgulanıyor...';

        try {
            const resp = await fetch(`/api/price/${encodeURIComponent(symbol)}`);
            const res = await resp.json();

            if (res.status === 'success' && res.price) {
                editBuyPrice.value = res.price;
                editPriceStatus.style.color = '#10b981';
                editPriceStatus.textContent = `✓ Güncel Fiyat: ₺${res.price.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`;
            } else {
                editPriceStatus.style.color = '#ef4444';
                editPriceStatus.textContent = res.message || 'Fiyat bilgisi alınamadı.';
            }
        } catch (err) {
            console.error('Fetch edit price error:', err);
            editPriceStatus.style.color = '#ef4444';
            editPriceStatus.textContent = 'Fiyat çekilirken hata oluştu.';
        } finally {
            fetchEditPriceBtn.disabled = false;
            fetchEditPriceBtn.textContent = '⚡ Güncel Fiyattan Al';
        }
    });

    // Pozisyon Ekle Form Submit
    addPositionForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        let symbol = addSymbol.value.trim().toUpperCase();
        const market = addMarket.value;

        if (market === '.IS' && !symbol.endsWith('.IS')) {
            symbol = symbol + '.IS';
        } else if (market === '-USD' && !symbol.endsWith('-USD')) {
            symbol = symbol + '-USD';
        }

        const payload = {
            symbol: symbol,
            lot: parseInt(addLot.value),
            buy_price: parseFloat(addBuyPrice.value),
            notes: addNotes.value.trim()
        };

        try {
            const response = await fetch('/api/portfolio/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const res = await response.json();

            if (res.status === 'success') {
                showAlert(res.message, 'success');
                addModal.classList.remove('show');
                loadPortfolio();
            } else {
                showAlert(res.message || 'Ekleme başarısız.', 'error');
            }
        } catch (error) {
            console.error('Add position error:', error);
            showAlert('İşlem sırasında bir hata oluştu.', 'error');
        }
    });

    // Pozisyon Düzenle Modalı Aç
    function openEditModal(pos) {
        editPositionId.value = pos.id;
        editSymbol.value = pos.symbol;
        editLot.value = pos.lot;
        editBuyPrice.value = pos.buy_price;
        editNotes.value = pos.notes || '';
        editPriceStatus.style.display = 'none';
        editModal.classList.add('show');
    }

    // Pozisyon Düzenle Form Submit
    editPositionForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            id: parseInt(editPositionId.value),
            lot: parseInt(editLot.value),
            buy_price: parseFloat(editBuyPrice.value),
            notes: editNotes.value.trim()
        };

        try {
            const response = await fetch('/api/portfolio/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const res = await response.json();

            if (res.status === 'success') {
                showAlert(res.message, 'success');
                editModal.classList.remove('show');
                loadPortfolio();
            } else {
                showAlert(res.message || 'Güncelleme başarısız.', 'error');
            }
        } catch (error) {
            console.error('Edit position error:', error);
            showAlert('Güncelleme sırasında hata oluştu.', 'error');
        }
    });

    // Yenile Butonları
    refreshBtn.addEventListener('click', () => {
        loadPortfolio();
        loadTargetStats();
    });

    refreshHistoryBtn.addEventListener('click', () => {
        loadTransactions();
        loadTargetStats();
    });

    // Sayfa Başlangıç Yüklemeleri
    loadTargetStats();
    loadPortfolio();
    loadTransactions();
});
