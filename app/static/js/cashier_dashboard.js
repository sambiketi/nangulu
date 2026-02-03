document.addEventListener('DOMContentLoaded', () => {
    const itemSelect = document.getElementById('item');
    const kgInput = document.getElementById('kg_sold');
    const priceDisplay = document.getElementById('price_per_kg');
    const totalDisplay = document.getElementById('total_price');
    const form = document.getElementById('sale-form');
    const recentSalesTbody = document.getElementById('recent-sales');

    // Debug: Log current inventory
    console.log("Current inventory data from template:");
    document.querySelectorAll('#inventory-table tr').forEach(row => {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 4) {
            console.log(`Item ${cells[0].textContent}: ${cells[1].textContent} - Stock: ${cells[3].textContent}`);
        }
    });

    function updateTotal() {
        const selectedOption = itemSelect.selectedOptions[0];
        const pricePerKg = parseFloat(selectedOption.dataset.price);
        const kgSold = parseFloat(kgInput.value) || 0;
        priceDisplay.textContent = pricePerKg.toFixed(2);
        totalDisplay.textContent = (pricePerKg * kgSold).toFixed(2);
    }

    itemSelect.addEventListener('change', updateTotal);
    kgInput.addEventListener('input', updateTotal);
    updateTotal();

    // NEW FUNCTION: Update inventory display after sale
    function updateInventoryDisplay(itemId, kgSold) {
        console.log(`Updating display for item ${itemId}, sold: ${kgSold}kg`);
        
        // Find the inventory table row for this item
        const inventoryRows = document.querySelectorAll('#inventory-table tr');
        let found = false;
        
        inventoryRows.forEach(row => {
            // Skip header row if present
            const itemIdCell = row.querySelector('td:first-child');
            if (itemIdCell) {
                const rowItemId = parseInt(itemIdCell.textContent.trim());
                
                if (rowItemId === itemId) {
                    found = true;
                    // Found the row! Update the stock cell (4th td)
                    const stockCell = row.querySelector('td:nth-child(4)'); // Stock column
                    if (stockCell) {
                        const currentStock = parseFloat(stockCell.textContent);
                        const newStock = currentStock - kgSold;
                        stockCell.textContent = newStock.toFixed(3);
                        console.log(`Updated item ${itemId} from ${currentStock} to ${newStock}`);
                    }
                }
            }
        });
        
        if (!found) {
            console.error(`Could not find inventory row for item ID: ${itemId}`);
            console.log('Available rows:', Array.from(inventoryRows).map(r => r.innerHTML));
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const data = {
            item_id: parseInt(itemSelect.value),
            kg_sold: parseFloat(kgInput.value),
            payment_type: document.getElementById('payment_type').value,
            customer_name: document.getElementById('customer_name').value
        };

        console.log('Submitting sale:', data);

        try {
            const resp = await fetch('/cashier/sales', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data),
                credentials: 'include'
            });

            const responseText = await resp.text();
            console.log('Response status:', resp.status);
            console.log('Response text:', responseText);
            
            if (!resp.ok) {
                throw new Error(`Sale failed: ${responseText}`);
            }

            const sale = JSON.parse(responseText);
            console.log('Sale successful:', sale);

            // 1. Add to recent sales table
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${sale.sale_number}</td>
                <td>${sale.item_name}</td>
                <td>${sale.kg_sold}</td>
                <td>${sale.total_price.toFixed(2)}</td>
                <td>${sale.created_at}</td>
            `;
            recentSalesTbody.prepend(tr);

            // 2. UPDATE INVENTORY DISPLAY
            updateInventoryDisplay(sale.item_id, sale.kg_sold);

            form.reset();
            updateTotal();
            alert(`Sale #${sale.sale_number} completed successfully!`);

        } catch (err) {
            console.error('Sale error:', err);
            alert(`Error: ${err.message}`);
        }
    });

    async function loadRecentSales() {
        try {
            const resp = await fetch('/cashier/sales/recent', {
                credentials: 'include'
            });
            if (!resp.ok) {
                console.error('Failed to load recent sales:', resp.status);
                return;
            }

            const sales = await resp.json();
            sales.forEach(sale => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${sale.sale_number}</td>
                    <td>${sale.item_name}</td>
                    <td>${sale.kg_sold}</td>
                    <td>${sale.total_price.toFixed(2)}</td>
                    <td>${sale.created_at}</td>
                `;
                recentSalesTbody.appendChild(tr);
            });
        } catch (err) {
            console.error('Error loading recent sales:', err);
        }
    }

    loadRecentSales();
});