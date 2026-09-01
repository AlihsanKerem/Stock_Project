document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('trackedTableBody');
    const addStockForm = document.getElementById('addStockForm');
    const newSymbolInput = document.getElementById('newSymbolInput');
    const addBtn = document.getElementById('addBtn');
    const messageBox = document.getElementById('messageBox');

    function showMessage(msg, isError = false) {
        messageBox.textContent = msg;
        messageBox.className = isError ? 'msg-error' : 'msg-success';
        messageBox.style.display = 'block';
        setTimeout(() => {
            messageBox.style.display = 'none';
        }, 5000);
    }

    function loadTrackedStocks() {
        fetch('/api/tracked')
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    renderTable(result.data);
                } else {
                    tableBody.innerHTML = `<tr><td colspan="4" style="color: var(--danger)">Hata: ${result.message}</td></tr>`;
                }
            })
            .catch(error => {
                tableBody.innerHTML = `<tr><td colspan="4" style="color: var(--danger)">Bağlantı hatası: ${error}</td></tr>`;
            });
    }

    function renderTable(data) {
        tableBody.innerHTML = '';

        if (data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center">Henüz takip edilen hisse yok.</td></tr>`;
            return;
        }

        data.forEach((stock, index) => {
            const tr = document.createElement('tr');
            tr.style.animationDelay = `${index * 0.02}s`;
            
            const price = stock.last_price !== null ? stock.last_price.toFixed(4) : 'Bekleniyor...';
            const updatedAt = stock.updated_at ? new Date(stock.updated_at).toLocaleString('tr-TR') : '-';

            tr.innerHTML = `
                <td class="symbol">${stock.symbol}</td>
                <td>${price}</td>
                <td>${updatedAt}</td>
                <td>
                    <button class="btn btn-danger remove-btn" data-symbol="${stock.symbol}">Sil</button>
                </td>
            `;
            tableBody.appendChild(tr);
        });

        // Add event listeners to remove buttons
        document.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const symbol = e.target.getAttribute('data-symbol');
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
        
        const marketExt = document.getElementById('marketType').value;
        if (marketExt !== 'CUSTOM') {
            symbol = symbol + marketExt;
        }

        addBtn.disabled = true;
        addBtn.textContent = 'Ekleniyor...';

        fetch('/api/tracked/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ symbol: symbol })
        })
        .then(response => response.json())
        .then(result => {
            addBtn.disabled = false;
            addBtn.textContent = 'Listeye Ekle';
            
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
            addBtn.textContent = 'Listeye Ekle';
            showMessage(`Bağlantı hatası: ${error}`, true);
        });
    });

    function removeStock(symbol) {
        fetch('/api/tracked/remove', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ symbol: symbol })
        })
        .then(response => response.json())
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

    // Initial load
    loadTrackedStocks();
});
