document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements - Full Table & Filters
    const tableBody = document.getElementById('tableBody');
    const searchInput = document.getElementById('searchInput');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const btnRunScan = document.getElementById('btnRunScan');
    const countAll = document.getElementById('countAll');

    // DOM Elements - KPIs
    const kpiPortfolioValue = document.getElementById('kpiPortfolioValue');
    const kpiPortfolioPnl = document.getElementById('kpiPortfolioPnl');
    const kpiTargetProfit = document.getElementById('kpiTargetProfit');
    const kpiTargetProgress = document.getElementById('kpiTargetProgress');
    const kpiSignalsCount = document.getElementById('kpiSignalsCount');
    const kpiSignalsSub = document.getElementById('kpiSignalsSub');
    const kpiAlertsCount = document.getElementById('kpiAlertsCount');
    const kpiAlertsSub = document.getElementById('kpiAlertsSub');

    // DOM Elements - Mini Widgets
    const miniPortfolioList = document.getElementById('miniPortfolioList');
    const miniTargetPct = document.getElementById('miniTargetPct');
    const miniTargetRemaining = document.getElementById('miniTargetRemaining');
    const miniProgressBar = document.getElementById('miniProgressBar');
    const miniRealizedPnl = document.getElementById('miniRealizedPnl');
    const miniTargetTotal = document.getElementById('miniTargetTotal');
    const miniSignalsList = document.getElementById('miniSignalsList');
    const topSignalCountBadge = document.getElementById('topSignalCountBadge');
    const miniAlertsList = document.getElementById('miniAlertsList');

    let rawStockData = [];
    let processedData = [];
    let currentFilter = 'all';
    let currentSort = { column: null, asc: true };
    let pieChartInstance = null;

    // Initial Dashboard & Table Load
    loadExecutiveDashboard();
    loadTableData();

    // 1. Load Executive Dashboard Summary (/api/dashboard/summary)
    function loadExecutiveDashboard() {
        fetch('/api/dashboard/summary')
            .then(res => res.json())
            .then(result => {
                if (result.status === 'success') {
                    const d = result.data;
                    renderKpis(d);
                    renderPortfolioWidget(d.portfolio);
                    renderTargetWidget(d.target);
                    renderSignalsWidget(d.signals);
                    renderAlertsWidget(d.alerts);
                }
            })
            .catch(err => {
                console.error('Dashboard özeti yüklenirken hata:', err);
            });
    }

    // Render KPI Cards
    function renderKpis(d) {
        // Portfolio KPI
        const p = d.portfolio;
        if (p) {
            kpiPortfolioValue.textContent = `₺${p.total_value.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`;
            const pnlSign = p.total_pnl >= 0 ? '+' : '';
            const pnlClass = p.total_pnl >= 0 ? 'color: #34d399;' : 'color: #ef4444;';
            kpiPortfolioPnl.innerHTML = `<span style="${pnlClass}">Net K/Z: ${pnlSign}₺${p.total_pnl.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} (${pnlSign}%${p.total_pnl_pct.toFixed(2)})</span>`;
        }

        // Target KPI
        const t = d.target;
        if (t) {
            const pnlSign = t.realized_pnl >= 0 ? '+' : '';
            kpiTargetProfit.textContent = `${pnlSign}₺${t.realized_pnl.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`;
            kpiTargetProfit.style.color = t.realized_pnl >= 0 ? '#34d399' : '#ef4444';
            kpiTargetProgress.textContent = `Hedef: ₺${t.monthly_target.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} (%${t.progress_pct}% tamamlandı)`;
        }

        // Signals KPI
        const s = d.signals;
        if (s) {
            kpiSignalsCount.textContent = s.total_count || 0;
            kpiSignalsSub.textContent = `Kısa: ${s.short_count} | Orta: ${s.med_count} | Uzun: ${s.long_count}`;
        }

        // Alerts KPI
        const a = d.alerts;
        if (a) {
            kpiAlertsCount.textContent = a.active_count || 0;
            kpiAlertsSub.textContent = `${a.active_count} aktif alarm takipte`;
        }
    }

    // Render Portfolio Donut Chart & Mini Positions
    function renderPortfolioWidget(portfolio) {
        if (!portfolio || !portfolio.positions || portfolio.positions.length === 0) {
            miniPortfolioList.innerHTML = `
                <div style="color: var(--text-secondary); text-align:center; padding: 1.5rem; font-size: 0.85rem;">
                    Portföyünüz henüz boş.<br>
                    <a href="/portfolio" style="color: var(--accent); text-decoration: none; margin-top: 0.5rem; display: inline-block;">+ Hisse Ekle</a>
                </div>
            `;
            initEmptyPieChart();
            return;
        }

        // Render Mini List
        miniPortfolioList.innerHTML = portfolio.positions.slice(0, 5).map(pos => {
            const pnlColor = pos.pnl >= 0 ? '#34d399' : '#ef4444';
            const pnlSign = pos.pnl >= 0 ? '+' : '';
            return `
                <div class="mini-item">
                    <div>
                        <span class="mini-sym">${pos.symbol}</span>
                        <span style="font-size: 0.75rem; color: var(--text-secondary); margin-left: 4px;">(${pos.lot} Lot)</span>
                    </div>
                    <div style="text-align: right;">
                        <span class="mini-val">₺${pos.current_value.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</span>
                        <span style="font-size: 0.75rem; color: ${pnlColor}; display: block;">${pnlSign}%${pos.pnl_pct.toFixed(2)}</span>
                    </div>
                </div>
            `;
        }).join('');

        // Render Chart.js Donut
        const labels = portfolio.positions.map(p => p.symbol);
        const dataValues = portfolio.positions.map(p => p.current_value);
        const bgColors = [
            '#38bdf8', '#10b981', '#f59e0b', '#c084fc', '#f43f5e', 
            '#06b6d4', '#84cc16', '#eab308', '#a855f7', '#ec4899'
        ];

        const ctx = document.getElementById('portfolioPieChart');
        if (ctx) {
            if (pieChartInstance) {
                pieChartInstance.destroy();
            }
            pieChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: dataValues,
                        backgroundColor: bgColors.slice(0, labels.length),
                        borderWidth: 0,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return ` ${context.label}: ₺${context.parsed.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`;
                                }
                            }
                        }
                    },
                    cutout: '70%'
                }
            });
        }
    }

    function initEmptyPieChart() {
        const ctx = document.getElementById('portfolioPieChart');
        if (ctx) {
            if (pieChartInstance) pieChartInstance.destroy();
            pieChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Boş'],
                    datasets: [{
                        data: [1],
                        backgroundColor: ['rgba(255,255,255,0.05)'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                    cutout: '75%'
                }
            });
        }
    }

    // Render Target Mini Progress
    function renderTargetWidget(target) {
        if (!target) return;
        const targetTl = target.monthly_target || 0;
        const realizedTl = target.realized_pnl || 0;
        const progressPct = Math.min(Math.max(target.progress_pct || 0, 0), 100);
        const remainingTl = target.remaining_tl || 0;

        if (miniTargetPct) miniTargetPct.textContent = `%${target.progress_pct || 0}`;
        if (miniTargetRemaining) miniTargetRemaining.textContent = `₺${remainingTl.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`;
        if (miniProgressBar) miniProgressBar.style.width = `${progressPct}%`;
        if (miniRealizedPnl) {
            miniRealizedPnl.textContent = `₺${realizedTl.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`;
            miniRealizedPnl.style.color = realizedTl >= 0 ? '#34d399' : '#ef4444';
        }
        if (miniTargetTotal) miniTargetTotal.textContent = `₺${targetTl.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}`;
    }

    // Render Top Signals Widget
    function renderSignalsWidget(signals) {
        if (!signals || !signals.items || signals.items.length === 0) {
            miniSignalsList.innerHTML = `
                <div style="color: var(--text-secondary); text-align:center; padding: 1.5rem; font-size: 0.85rem;">
                    Bugün için tetiklenen yeni sinyal yok.<br>
                    <span style="font-size: 0.75rem;">Canlı tarama yapmak için aşağıdaki butonu kullanabilirsiniz.</span>
                </div>
            `;
            if (topSignalCountBadge) topSignalCountBadge.textContent = '0 Sinyal';
            return;
        }

        if (topSignalCountBadge) topSignalCountBadge.textContent = `${signals.items.length} Sinyal`;

        miniSignalsList.innerHTML = signals.items.slice(0, 4).map(sig => {
            const sym = (sig.symbol || '').replace('.IS', '');
            const badgeClass = sig.timeframe_key === 'SHORT' ? 'short' : sig.timeframe_key === 'MEDIUM' ? 'medium' : 'long';
            const price = sig.price_at_signal ? `₺${sig.price_at_signal.toFixed(2)}` : '';
            return `
                <div class="mini-item">
                    <div>
                        <a href="/hisse-analiz?symbol=${sym}" style="text-decoration: none; color: inherit;">
                            <span class="mini-sym">${sym}</span>
                        </a>
                        <span class="timeframe-badge ${badgeClass}" style="margin-left: 6px; font-size: 0.7rem; padding: 0.15rem 0.4rem;">${sig.signal_name || sig.signal_type}</span>
                    </div>
                    <div style="text-align: right;">
                        <span class="target-badge" style="font-size: 0.75rem;">${sig.target_return || '-'}</span>
                        <span style="font-size: 0.75rem; color: var(--text-secondary); margin-left: 4px;">${price}</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Render Alerts Widget
    function renderAlertsWidget(alerts) {
        if (!alerts || !alerts.items || alerts.items.length === 0) {
            miniAlertsList.innerHTML = `
                <div style="color: var(--text-secondary); text-align:center; padding: 1.5rem; font-size: 0.85rem;">
                    Kurulmuş aktif alarm bulunmuyor.<br>
                    <a href="/takip" style="color: var(--accent); text-decoration: none; margin-top: 0.5rem; display: inline-block;">+ Alarm Kur</a>
                </div>
            `;
            return;
        }

        miniAlertsList.innerHTML = alerts.items.slice(0, 4).map(al => {
            const sym = (al.symbol || '').replace('.IS', '');
            const isTriggered = al.status === 'TRIGGERED';
            const dirIcon = al.direction === 'UP' ? '📈' : '📉';
            const pctText = (al.target_percentage >= 0 ? '+' : '') + al.target_percentage.toFixed(2) + '%';
            const badgeStyle = isTriggered 
                ? 'background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3);' 
                : 'background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56,189,248,0.3);';
            const statusLabel = isTriggered ? 'TETİKLENDİ' : 'AKTİF';

            return `
                <div class="mini-item">
                    <div>
                        <span class="mini-sym">${sym}</span>
                        <span style="font-size: 0.75rem; margin-left: 6px;">${dirIcon} ${pctText} (₺${al.target_price.toFixed(2)})</span>
                    </div>
                    <div>
                        <span style="display: inline-block; padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; ${badgeStyle}">
                            ${statusLabel}
                        </span>
                    </div>
                </div>
            `;
        }).join('');
    }

    // 2. Load Full BIST Table Data (/api/data)
    function loadTableData() {
        tableBody.innerHTML = `
            <tr class="loading-row">
                <td colspan="11" style="text-align:center; padding: 2rem; color: var(--text-secondary);">
                    ⏳ Veriler yükleniyor, lütfen bekleyin...
                </td>
            </tr>
        `;

        fetch('/api/data')
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    rawStockData = result.data || [];
                    processedData = processStockData(rawStockData);
                    if (countAll) countAll.textContent = processedData.length;
                    applyFilterAndRender();
                } else {
                    tableBody.innerHTML = `<tr><td colspan="11" style="color: var(--danger); text-align:center; padding: 2rem;">Hata: ${result.message}</td></tr>`;
                }
            })
            .catch(error => {
                tableBody.innerHTML = `<tr><td colspan="11" style="color: var(--danger); text-align:center; padding: 2rem;">Bağlantı hatası: ${error}</td></tr>`;
            });
    }

    // Process raw stock data and derive timeframe, risk & backtest stats
    function processStockData(data) {
        return data.map(item => {
            const signals = item.signals ? item.signals : '';
            const sigList = signals ? signals.split(', ').map(s => s.trim()) : [];
            const details = item.signal_details || [];
            
            let timeframes = [];
            let timeframeKeys = [];
            let actions = [];
            let targetReturns = [];
            let winRates = [];
            let isConflict = item.is_conflict || false;

            if (Array.isArray(details) && details.length > 0) {
                details.forEach(d => {
                    const tfKey = d.timeframe_key || 'SHORT';
                    timeframeKeys.push(tfKey);
                    actions.push(d.action || 'BUY');
                    if (d.win_rate) {
                        winRates.push({
                            name: d.name,
                            win_rate: d.win_rate,
                            avg_return: d.avg_return,
                            excess_return: d.excess_return,
                            is_validated: d.is_validated,
                            sample_size: d.sample_size
                        });
                    }
                    if (d.is_conflict) isConflict = true;
                });
            } else {
                // Fallback to text parsing
                if (sigList.includes('Haftalık Al-Sat') || sigList.includes('Hacim Patlaması')) {
                    timeframeKeys.push('SHORT');
                    actions.push('BUY');
                }
                if (sigList.includes('Aylık Al-Sat')) {
                    timeframeKeys.push('MEDIUM');
                    actions.push('BUY');
                }
                if (sigList.includes('Değer Avcısı') || sigList.includes('Temettü Kalesi')) {
                    timeframeKeys.push('LONG');
                    actions.push('BUY');
                }
                if (sigList.includes('Aşırı Alım / Risk')) {
                    timeframeKeys.push('SHORT');
                    actions.push('SELL');
                }
                if (sigList.includes('Trend Kırılımı (SAT)')) {
                    timeframeKeys.push('MEDIUM');
                    actions.push('SELL');
                }
                if (sigList.includes('Aşırı Değerleme (Uzak Dur)')) {
                    timeframeKeys.push('LONG');
                    actions.push('SELL');
                }
            }

            timeframeKeys = [...new Set(timeframeKeys)];
            const hasBuy = actions.includes('BUY');
            const hasSell = actions.includes('SELL');
            if (hasBuy && hasSell) isConflict = true;

            const primaryAction = isConflict ? 'CONFLICT' : (hasSell ? 'SELL' : (hasBuy ? 'BUY' : 'NONE'));

            return {
                ...item,
                signalList: sigList,
                signalDetails: details,
                timeframeKeys: timeframeKeys,
                primaryTimeframe: timeframeKeys[0] || 'NONE',
                actions: actions,
                primaryAction: primaryAction,
                isConflict: isConflict,
                winRates: winRates
            };
        });
    }

    // Filter Buttons Click
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.timeframe;
            applyFilterAndRender();
        });
    });

    // Search Input
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            applyFilterAndRender();
        });
    }

    // Run Scan Button
    if (btnRunScan) {
        btnRunScan.addEventListener('click', () => {
            btnRunScan.disabled = true;
            btnRunScan.innerHTML = `<span>⏳</span> Taranıyor...`;
            
            fetch('/api/signals/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert(data.message || 'Tarama tamamlandı!');
                    loadExecutiveDashboard();
                    loadTableData();
                } else {
                    alert('Hata: ' + data.message);
                }
            })
            .catch(err => {
                alert('Tarama sırasında hata oluştu: ' + err);
            })
            .finally(() => {
                btnRunScan.disabled = false;
                btnRunScan.innerHTML = `<span>⚡</span> Canlı Tarama Yap`;
            });
        });
    }

    // Backtest Modal Elements & Handlers
    const backtestModal = document.getElementById('backtestModal');
    const btnOpenBacktestModal = document.getElementById('btnOpenBacktestModal');
    const btnCloseBacktestModal = document.getElementById('btnCloseBacktestModal');
    const backtestTableBody = document.getElementById('backtestTableBody');
    const btnRerunBacktest = document.getElementById('btnRerunBacktest');

    if (btnOpenBacktestModal && backtestModal) {
        btnOpenBacktestModal.addEventListener('click', () => {
            backtestModal.style.display = 'flex';
            loadBacktestTable();
        });
    }

    if (btnCloseBacktestModal && backtestModal) {
        btnCloseBacktestModal.addEventListener('click', () => {
            backtestModal.style.display = 'none';
        });
    }

    // Modal dışına tıklayınca kapatma
    window.addEventListener('click', (e) => {
        if (e.target === backtestModal) {
            backtestModal.style.display = 'none';
        }
    });

    function loadBacktestTable() {
        if (!backtestTableBody) return;
        backtestTableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 1.5rem; color: var(--text-secondary);">⏳ İstatistikler alınıyor...</td></tr>`;

        fetch('/api/backtest/stats')
            .then(res => res.json())
            .then(result => {
                if (result.status === 'success' && result.data) {
                    renderBacktestModalTable(result.data);
                } else {
                    backtestTableBody.innerHTML = `<tr><td colspan="9" style="color: var(--danger); text-align: center;">Hata: ${result.message}</td></tr>`;
                }
            })
            .catch(err => {
                backtestTableBody.innerHTML = `<tr><td colspan="9" style="color: var(--danger); text-align: center;">Bağlantı hatası: ${err}</td></tr>`;
            });
    }

    function renderBacktestModalTable(dataList) {
        if (!backtestTableBody) return;
        if (!dataList || dataList.length === 0) {
            backtestTableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 1.5rem;">Kayıtlı backtest istatistiği bulunamadı.</td></tr>`;
            return;
        }

        backtestTableBody.innerHTML = dataList.map(item => {
            const isBuy = !item.signal_type.includes('risk') && !item.signal_type.includes('kirilimi') && !item.signal_type.includes('pahali');
            const dirBadge = isBuy 
                ? `<span class="badge-buy">AL</span>` 
                : `<span class="badge-sell">SAT / RİSK</span>`;
            
            const winColor = item.win_rate >= 60 ? '#34d399' : (item.win_rate >= 50 ? '#38bdf8' : '#fbbf24');
            const retSign = item.avg_return >= 0 ? '+' : '';
            const retColor = item.avg_return >= 0 ? '#34d399' : '#f43f5e';
            const excessSign = item.excess_return >= 0 ? '+' : '';
            const excessColor = item.excess_return >= 0 ? '#34d399' : '#f43f5e';

            const oosBadge = item.is_validated 
                ? `<span class="badge-oos-ok">✓ Onaylandı</span>` 
                : `<span class="badge-oos-warn">⚠️ Sapma Var</span>`;

            const tfLabel = item.timeframe_key === 'SHORT' ? 'Kısa (7G)' : (item.timeframe_key === 'MEDIUM' ? 'Orta (20G)' : 'Uzun (60G)');

            return `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="font-weight: 600; color: #fff;">${item.signal_name}</td>
                    <td>${dirBadge}</td>
                    <td>${tfLabel}</td>
                    <td style="font-weight: 600;">${item.sample_size}</td>
                    <td style="color: ${winColor}; font-weight: 700;">%${item.win_rate.toFixed(1)}</td>
                    <td style="color: ${retColor}; font-weight: 600;">${retSign}%${item.avg_return.toFixed(2)}</td>
                    <td style="color: ${excessColor}; font-weight: 600;">${excessSign}%${item.excess_return.toFixed(2)}</td>
                    <td style="color: #f43f5e;">%${item.max_loss.toFixed(1)}</td>
                    <td>${oosBadge}</td>
                </tr>
            `;
        }).join('');
    }

    if (btnRerunBacktest) {
        btnRerunBacktest.addEventListener('click', () => {
            btnRerunBacktest.disabled = true;
            btnRerunBacktest.innerHTML = `<span>⏳</span> 5 Yıllık Veriler Hesaplanıyor...`;

            fetch('/api/backtest/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ period: '5y' })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert('✓ 5 Yıllık Backtest ve Out-of-Sample doğrulama başarıyla tamamlandı!');
                    loadBacktestTable();
                    loadTableData();
                } else {
                    alert('Backtest hatası: ' + data.message);
                }
            })
            .catch(err => {
                alert('Backtest çalıştırılırken hata: ' + err);
            })
            .finally(() => {
                btnRerunBacktest.disabled = false;
                btnRerunBacktest.innerHTML = `<span>🚀</span> Backtest'i Yeniden Hesapla`;
            });
        });
    }

    // Sorting Logic
    const headers = document.querySelectorAll('th[data-sort]');
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            if (currentSort.column === column) {
                currentSort.asc = !currentSort.asc;
            } else {
                currentSort.column = column;
                currentSort.asc = true;
            }

            headers.forEach(h => {
                h.textContent = h.textContent.replace(' ↑', '').replace(' ↓', '');
            });
            header.textContent += currentSort.asc ? ' ↑' : ' ↓';

            applyFilterAndRender();
        });
    });

    function applyFilterAndRender() {
        const searchTerm = (searchInput ? searchInput.value : '').toLowerCase().trim();

        // 1. Filter
        let filtered = processedData.filter(stock => {
            let passFilter = true;
            if (currentFilter === 'SHORT') {
                passFilter = stock.timeframeKeys.includes('SHORT');
            } else if (currentFilter === 'MEDIUM') {
                passFilter = stock.timeframeKeys.includes('MEDIUM');
            } else if (currentFilter === 'LONG') {
                passFilter = stock.timeframeKeys.includes('LONG');
            } else if (currentFilter === 'BUY_ONLY') {
                passFilter = stock.primaryAction === 'BUY' || (stock.actions && stock.actions.includes('BUY'));
            } else if (currentFilter === 'SELL_ONLY') {
                passFilter = stock.primaryAction === 'SELL' || (stock.actions && stock.actions.includes('SELL'));
            } else if (currentFilter === 'CONFLICT_ONLY') {
                passFilter = stock.isConflict === true;
            }

            if (!passFilter) return false;

            if (searchTerm) {
                const sym = (stock.symbol || '').toLowerCase();
                const sigs = (stock.signals || '').toLowerCase();
                return sym.includes(searchTerm) || sigs.includes(searchTerm);
            }

            return true;
        });

        // 2. Sort
        if (currentSort.column) {
            const col = currentSort.column;
            filtered.sort((a, b) => {
                let valA = a[col];
                let valB = b[col];

                if (valA === null || valA === undefined) valA = currentSort.asc ? Infinity : -Infinity;
                if (valB === null || valB === undefined) valB = currentSort.asc ? Infinity : -Infinity;

                if (typeof valA === 'string') valA = valA.toLowerCase();
                if (typeof valB === 'string') valB = valB.toLowerCase();

                if (valA < valB) return currentSort.asc ? -1 : 1;
                if (valA > valB) return currentSort.asc ? 1 : -1;
                return 0;
            });
        }

        renderTable(filtered);
    }

    function renderTable(data) {
        tableBody.innerHTML = '';

        if (data.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="11" style="text-align:center; padding: 3rem; color: var(--text-secondary);">
                        🔍 Seçilen kriterlere uygun hisse veya sinyal bulunamadı.
                    </td>
                </tr>
            `;
            return;
        }

        data.forEach((stock, index) => {
            const tr = document.createElement('tr');
            tr.style.animationDelay = `${Math.min(index * 0.02, 0.5)}s`;

            const price = stock.price ? `₺${stock.price.toFixed(2)}` : '-';
            const pb = stock.pb_ratio ? stock.pb_ratio.toFixed(2) : '-';
            const pe = stock.pe_ratio ? stock.pe_ratio.toFixed(2) : '-';

            // RSI with color
            let rsiHtml = '-';
            if (stock.rsi) {
                const rsiVal = stock.rsi.toFixed(1);
                if (stock.rsi < 30) rsiHtml = `<span class="rsi-low">⚡ ${rsiVal}</span>`;
                else if (stock.rsi > 70) rsiHtml = `<span class="rsi-high">🔥 ${rsiVal}</span>`;
                else rsiHtml = `<span>${rsiVal}</span>`;
            }

            // Vade & Yön Badge
            let tfHtml = '<span style="color: var(--text-secondary); font-size: 0.8rem;">-</span>';
            if (stock.isConflict) {
                tfHtml = `<span class="badge-conflict">⚠️ ÇELİŞKİ</span>`;
            } else if (stock.timeframeKeys && stock.timeframeKeys.length > 0) {
                const tfBadges = stock.timeframeKeys.map(tf => {
                    const cls = tf === 'SHORT' ? 'short' : (tf === 'MEDIUM' ? 'medium' : 'long');
                    const label = tf === 'SHORT' ? 'Kısa (1-7G)' : (tf === 'MEDIUM' ? 'Orta (1-4H)' : 'Uzun (Değer)');
                    return `<span class="timeframe-badge ${cls}">${label}</span>`;
                });
                tfHtml = tfBadges.join(' ');
            }

            // Sinyal Rozetleri (AL / SAT / Çakışma)
            let signalsHtml = '<span style="color: var(--text-secondary); font-size: 0.8rem;">Sinyal Yok</span>';
            if (stock.signalList && stock.signalList.length > 0) {
                signalsHtml = stock.signalList.map(sig => {
                    if (sig.includes('Aşırı Alım') || sig.includes('Trend Kırılımı') || sig.includes('Aşırı Değerleme')) {
                        return `<span class="badge-sell" style="margin-right: 4px; display: inline-block; margin-bottom: 2px;">🔴 ${sig}</span>`;
                    } else if (stock.isConflict) {
                        return `<span class="badge-conflict" style="margin-right: 4px; display: inline-block; margin-bottom: 2px;">${sig}</span>`;
                    } else {
                        return `<span class="badge-buy" style="margin-right: 4px; display: inline-block; margin-bottom: 2px;">🟢 ${sig}</span>`;
                    }
                }).join('');
            }

            // Ölçülen Başarı (Gerçek Backtest İstatistiği)
            let backtestHtml = '<span style="color: var(--text-secondary); font-size: 0.8rem;">-</span>';
            if (stock.winRates && stock.winRates.length > 0) {
                backtestHtml = stock.winRates.map(w => {
                    const retSign = w.avg_return >= 0 ? '+' : '';
                    const sampleWarn = w.sample_size < 30 ? '<span title="N<30 Düşük Örneklem" style="color: #fbbf24;"> ⚠️</span>' : '';
                    return `
                        <div class="stat-win-badge" title="Tetiklenme: ${w.sample_size} işlem | XU100 Farkı: ${w.excess_return >= 0 ? '+' : ''}%${w.excess_return}%">
                            Kazanma: %${w.win_rate.toFixed(0)} (Ort: ${retSign}%${w.avg_return.toFixed(1)})${sampleWarn}
                        </div>
                    `;
                }).join('<br>');
            }

            // Stop-Loss & ATR
            let stopLossHtml = '<span style="color: var(--text-secondary); font-size: 0.8rem;">-</span>';
            if (stock.stop_loss) {
                const atrStr = stock.atr ? `(ATR: ₺${stock.atr.toFixed(2)})` : '';
                stopLossHtml = `
                    <div style="font-size: 0.8rem; font-weight: 600; color: #f43f5e;">
                        ₺${stock.stop_loss.toFixed(2)}
                        <span style="font-size: 0.7rem; color: var(--text-secondary); display: block; font-weight: 400;">${atrStr}</span>
                    </div>
                `;
            }

            // Risk & Volatilite
            let riskHtml = '-';
            if (stock.volatility) {
                const rLevel = stock.risk_level || (stock.volatility < 35 ? 'Düşük Risk' : (stock.volatility <= 55 ? 'Orta Risk' : 'Yüksek Risk'));
                const rClass = stock.volatility < 35 ? 'low' : (stock.volatility <= 55 ? 'medium' : 'high');
                riskHtml = `
                    <span class="risk-tag ${rClass}">%${stock.volatility.toFixed(1)} (${rLevel})</span>
                `;
            }

            // Actions
            const cleanSymbol = stock.symbol.replace('.IS', '');
            const actionsHtml = `
                <div style="display: flex; gap: 0.4rem;">
                    <a href="/hisse-analiz?symbol=${cleanSymbol}" class="btn-sm btn-outline" title="Detaylı Analiz & AI Yorumu">🎯 Analiz</a>
                    <a href="/portfolio?add=${cleanSymbol}" class="btn-sm btn-outline" style="border-color: rgba(16, 185, 129, 0.3); color: #34d399;" title="Portföye Ekle">💼 Al</a>
                </div>
            `;

            tr.innerHTML = `
                <td class="symbol">
                    <a href="/hisse-analiz?symbol=${cleanSymbol}" style="color: inherit; text-decoration: none; font-weight: 700;">
                        ${cleanSymbol}
                    </a>
                </td>
                <td style="font-weight: 600;">${price}</td>
                <td>${tfHtml}</td>
                <td>${signalsHtml}</td>
                <td>${backtestHtml}</td>
                <td>${stopLossHtml}</td>
                <td>${riskHtml}</td>
                <td>${rsiHtml}</td>
                <td>${pb}</td>
                <td>${pe}</td>
                <td>${actionsHtml}</td>
            `;

            tableBody.appendChild(tr);
        });
    }
});


