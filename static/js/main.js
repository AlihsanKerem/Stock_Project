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
                <td colspan="10" style="text-align:center; padding: 2rem; color: var(--text-secondary);">
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
                    tableBody.innerHTML = `<tr><td colspan="10" style="color: var(--danger); text-align:center; padding: 2rem;">Hata: ${result.message}</td></tr>`;
                }
            })
            .catch(error => {
                tableBody.innerHTML = `<tr><td colspan="10" style="color: var(--danger); text-align:center; padding: 2rem;">Bağlantı hatası: ${error}</td></tr>`;
            });
    }

    // Process raw stock data and derive timeframe & target returns
    function processStockData(data) {
        return data.map(item => {
            const signals = item.signals ? item.signals : '';
            const sigList = signals ? signals.split(', ').map(s => s.trim()) : [];
            
            let timeframes = [];
            let targetReturns = [];
            let timeframeKeys = [];

            if (sigList.includes('Haftalık Al-Sat')) {
                timeframeKeys.push('SHORT');
                timeframes.push({ label: '⚡ Kısa Vade (1-7 Gün)', class: 'short' });
                targetReturns.push('%2.5 - %5');
            }
            if (sigList.includes('Hacim Patlaması')) {
                timeframeKeys.push('SHORT');
                timeframes.push({ label: '⚡ Kısa Vade (1-7 Gün)', class: 'short' });
                targetReturns.push('%3 - %7');
            }
            if (sigList.includes('Aylık Al-Sat')) {
                timeframeKeys.push('MEDIUM');
                timeframes.push({ label: '📈 Orta Vade (1-4 Hafta)', class: 'medium' });
                targetReturns.push('%5 - %12');
            }
            if (sigList.includes('Değer Avcısı')) {
                timeframeKeys.push('LONG');
                timeframes.push({ label: '💎 Uzun Vade (Değer)', class: 'long' });
                targetReturns.push('%15 - %30+');
            }
            if (sigList.includes('Temettü Kalesi')) {
                timeframeKeys.push('LONG');
                timeframes.push({ label: '💎 Uzun Vade (Temettü)', class: 'long' });
                targetReturns.push('%10 - %25+');
            }

            timeframeKeys = [...new Set(timeframeKeys)];

            return {
                ...item,
                signalList: sigList,
                timeframes: timeframes,
                timeframeKeys: timeframeKeys,
                primaryTimeframe: timeframeKeys[0] || 'NONE',
                targetReturnText: targetReturns.length > 0 ? targetReturns.join(' / ') : '-'
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
    searchInput.addEventListener('input', () => {
        applyFilterAndRender();
    });

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
        const searchTerm = searchInput.value.toLowerCase().trim();

        // 1. Filter
        let filtered = processedData.filter(stock => {
            let passTimeframe = true;
            if (currentFilter === 'SHORT') {
                passTimeframe = stock.timeframeKeys.includes('SHORT');
            } else if (currentFilter === 'MEDIUM') {
                passTimeframe = stock.timeframeKeys.includes('MEDIUM');
            } else if (currentFilter === 'LONG') {
                passTimeframe = stock.timeframeKeys.includes('LONG');
            } else if (currentFilter === 'SIGNALS_ONLY') {
                passTimeframe = stock.signalList.length > 0;
            }

            if (!passTimeframe) return false;

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
                    <td colspan="10" style="text-align:center; padding: 3rem; color: var(--text-secondary);">
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
            const div = stock.div_yield ? `%${stock.div_yield.toFixed(2)}` : '-';

            // RSI with color
            let rsiHtml = '-';
            if (stock.rsi) {
                const rsiVal = stock.rsi.toFixed(2);
                if (stock.rsi < 30) rsiHtml = `<span class="rsi-low">⚡ ${rsiVal} (Aşırı Satım)</span>`;
                else if (stock.rsi > 70) rsiHtml = `<span class="rsi-high">🔥 ${rsiVal} (Aşırı Alım)</span>`;
                else rsiHtml = `<span>${rsiVal}</span>`;
            }

            // Timeframe badge
            let tfHtml = '<span style="color: var(--text-secondary); font-size: 0.8rem;">-</span>';
            if (stock.timeframes && stock.timeframes.length > 0) {
                const uniqueTf = [];
                const seen = new Set();
                for (const tf of stock.timeframes) {
                    if (!seen.has(tf.label)) {
                        seen.add(tf.label);
                        uniqueTf.push(tf);
                    }
                }
                tfHtml = uniqueTf.map(tf => `<span class="timeframe-badge ${tf.class}">${tf.label}</span>`).join(' ');
            }

            // Signals badge
            let signalsHtml = '<span style="color: var(--text-secondary); font-size: 0.8rem;">Sinyal Yok</span>';
            if (stock.signalList && stock.signalList.length > 0) {
                signalsHtml = stock.signalList.map(sig => {
                    if (sig === 'Değer Avcısı') return `<span class="signal-badge">${sig}</span>`;
                    if (sig === 'Hacim Patlaması') return `<span class="signal-badge warning">${sig}</span>`;
                    if (sig === 'Haftalık Al-Sat') return `<span class="signal-badge warning">${sig}</span>`;
                    if (sig === 'Aylık Al-Sat') return `<span class="signal-badge info">${sig}</span>`;
                    if (sig === 'Temettü Kalesi') return `<span class="signal-badge purple">${sig}</span>`;
                    return `<span class="signal-badge">${sig}</span>`;
                }).join('');
            }

            // Target return
            let targetHtml = '-';
            if (stock.targetReturnText && stock.targetReturnText !== '-') {
                targetHtml = `<span class="target-badge">${stock.targetReturnText}</span>`;
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
                <td>${targetHtml}</td>
                <td>${rsiHtml}</td>
                <td>${pb}</td>
                <td>${pe}</td>
                <td>${div}</td>
                <td>${actionsHtml}</td>
            `;

            tableBody.appendChild(tr);
        });
    }
});

