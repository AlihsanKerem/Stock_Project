document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('tableBody');
    const searchInput = document.getElementById('searchInput');
    let stockData = [];

    // Fetch data from API
    fetch('/api/data')
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                stockData = result.data;
                renderTable(stockData);
            } else {
                tableBody.innerHTML = `<tr><td colspan="7" style="color: var(--danger)">Hata: ${result.message}</td></tr>`;
            }
        })
        .catch(error => {
            tableBody.innerHTML = `<tr><td colspan="7" style="color: var(--danger)">Bağlantı hatası: ${error}</td></tr>`;
        });

    // Search functionality
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredData = stockData.filter(stock => 
            stock.symbol.toLowerCase().includes(searchTerm) || 
            (stock.signals && stock.signals.toLowerCase().includes(searchTerm))
        );
        renderTable(filteredData);
    });

    // Sort functionality
    const headers = document.querySelectorAll('th[data-sort]');
    let currentSort = { column: null, asc: true };

    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            
            // Toggle sort direction
            if (currentSort.column === column) {
                currentSort.asc = !currentSort.asc;
            } else {
                currentSort.column = column;
                currentSort.asc = true;
            }

            // Perform sort
            const sortedData = [...stockData].sort((a, b) => {
                let valA = a[column];
                let valB = b[column];

                // Handle nulls
                if (valA === null) valA = currentSort.asc ? Infinity : -Infinity;
                if (valB === null) valB = currentSort.asc ? Infinity : -Infinity;

                if (valA < valB) return currentSort.asc ? -1 : 1;
                if (valA > valB) return currentSort.asc ? 1 : -1;
                return 0;
            });

            // Update UI
            headers.forEach(h => h.textContent = h.textContent.replace(' ↑', '').replace(' ↓', ''));
            header.textContent += currentSort.asc ? ' ↑' : ' ↓';

            // We only re-render the sorted data if we're not currently searching, 
            // but for simplicity let's just sort the current view or re-render all
            // To be accurate with search, we should sort the filtered data
            const searchTerm = searchInput.value.toLowerCase();
            const filteredAndSortedData = sortedData.filter(stock => 
                stock.symbol.toLowerCase().includes(searchTerm) || 
                (stock.signals && stock.signals.toLowerCase().includes(searchTerm))
            );
            
            renderTable(filteredAndSortedData);
        });
    });

    function renderTable(data) {
        tableBody.innerHTML = '';

        if (data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center">Sonuç bulunamadı.</td></tr>`;
            return;
        }

        data.forEach((stock, index) => {
            const tr = document.createElement('tr');
            tr.style.animationDelay = `${index * 0.02}s`; // Staggered animation
            
            // Format values
            const price = stock.price ? stock.price.toFixed(2) : '-';
            const pb = stock.pb_ratio ? stock.pb_ratio.toFixed(2) : '-';
            const pe = stock.pe_ratio ? stock.pe_ratio.toFixed(2) : '-';
            const div = stock.div_yield ? stock.div_yield.toFixed(2) : '-';
            
            // Format RSI with colors
            let rsiHtml = '-';
            if (stock.rsi) {
                const rsiVal = stock.rsi.toFixed(2);
                if (stock.rsi < 30) rsiHtml = `<span class="rsi-low">${rsiVal}</span>`;
                else if (stock.rsi > 70) rsiHtml = `<span class="rsi-high">${rsiVal}</span>`;
                else rsiHtml = rsiVal;
            }

            // Format Signals
            let signalsHtml = '-';
            if (stock.signals) {
                const signalsList = stock.signals.split(', ');
                signalsHtml = signalsList.map(sig => {
                    if (sig === 'Değer Avcısı') return `<span class="signal-badge">${sig}</span>`;
                    if (sig === 'Hacim Patlaması') return `<span class="signal-badge warning">${sig}</span>`;
                    if (sig === 'Al-Sat Fırsatı') return `<span class="signal-badge info">${sig}</span>`;
                    return `<span class="signal-badge">${sig}</span>`;
                }).join('');
            }

            tr.innerHTML = `
                <td class="symbol">${stock.symbol}</td>
                <td>${price}</td>
                <td>${rsiHtml}</td>
                <td>${pb}</td>
                <td>${pe}</td>
                <td>${div}</td>
                <td>${signalsHtml}</td>
            `;
            
            tableBody.appendChild(tr);
        });
    }
});
