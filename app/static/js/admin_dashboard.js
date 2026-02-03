// ----------------- Cashiers -----------------
async function addCashier() {
    const username = prompt("Enter cashier username:");
    const fullName = prompt("Enter full name:");
    const password = prompt("Enter password:");

    if (!username || !fullName || !password) return alert("All fields are required");

    try {
        const resp = await fetch('/api/admin/cashiers', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, full_name: fullName, password}),
            credentials: 'include'
        });

        if (resp.ok) {
            location.reload();
        } else {
            const error = await resp.text();
            alert("Error adding cashier: " + error);
        }
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// ----------------- Inventory -----------------
// NEW FUNCTION: Set purchase price
async function setPurchasePrice(itemId) {
    const input = document.querySelector(`input[data-id='${itemId}'][data-field='purchase_price']`);
    const price = parseFloat(input.value);
    if (isNaN(price) || price <= 0) return alert("Invalid purchase price (must be > 0)");

    try {
        const resp = await fetch(`/api/admin/inventory/${itemId}/purchase-price`, {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({purchase_price_per_kg: price}),
            credentials: 'include'
        });

        const responseText = await resp.text();
        console.log('Set purchase price response:', resp.status, responseText);
        
        if (resp.ok) {
            location.reload();
        } else {
            alert("Error updating purchase price: " + responseText);
        }
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// EXISTING FUNCTION: Set selling price (kept as is)
async function setPrice(itemId) {
    const input = document.querySelector(`input[data-id='${itemId}'][data-field='selling_price']`);
    const price = parseFloat(input.value);
    if (isNaN(price) || price <= 0) return alert("Invalid selling price (must be > 0)");

    try {
        const resp = await fetch(`/api/admin/inventory/${itemId}/price`, {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({current_price_per_kg: price}),
            credentials: 'include'
        });

        const responseText = await resp.text();
        console.log('Set selling price response:', resp.status, responseText);
        
        if (resp.ok) {
            location.reload();
        } else {
            alert("Error updating selling price: " + responseText);
        }
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// EXISTING FUNCTION: Add stock (kept as is with minor improvement)
async function addPurchase(itemId) {
    // If no itemId provided, we're creating a new item
    if (!itemId) {
        return addNewItem();
    }
    
    // Otherwise, add stock to existing item
    const qty = prompt("Enter quantity to add (kg):");
    if (!qty || isNaN(qty) || parseFloat(qty) <= 0) {
        return alert("Invalid quantity (must be > 0)");
    }
    
    // Try to get purchase price from input field first
    const purchasePriceInput = document.querySelector(`input[data-id='${itemId}'][data-field='purchase_price']`);
    let purchasePrice = null;
    
    if (purchasePriceInput && purchasePriceInput.value) {
        purchasePrice = parseFloat(purchasePriceInput.value);
        if (!isNaN(purchasePrice) && purchasePrice > 0) {
            console.log("Using purchase price from field:", purchasePrice);
        } else {
            purchasePrice = null;
        }
    }
    
    // If no purchase price in field, ask user
    if (!purchasePrice) {
        const price = prompt("Enter purchase price per kg (optional, press Cancel to skip):");
        purchasePrice = price && !isNaN(price) && parseFloat(price) > 0 ? parseFloat(price) : null;
    }

    try {
        const resp = await fetch('/api/admin/purchases', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                item_id: itemId,
                kg_added: parseFloat(qty),
                purchase_price_per_kg: purchasePrice
            }),
            credentials: 'include'
        });

        const responseText = await resp.text();
        console.log('Add stock response:', resp.status, responseText);
        
        if (resp.ok) {
            location.reload();
        } else {
            alert("Error adding stock: " + responseText);
        }
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// EXISTING FUNCTION: Add new item (kept as is)
async function addNewItem() {
    const name = prompt("Enter item name:");
    if (!name) return alert("Item name is required");
    
    const description = prompt("Enter item description (optional):");
    const qty = prompt("Enter initial quantity (kg):");
    if (!qty || isNaN(qty) || parseFloat(qty) < 0) {
        return alert("Invalid quantity");
    }
    
    const price = prompt("Enter purchase price per kg:");
    if (!price || isNaN(price) || parseFloat(price) <= 0) {
        return alert("Valid price is required for new items");
    }

    try {
        const resp = await fetch('/api/admin/purchases', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: name,
                description: description || "",
                kg_added: parseFloat(qty),
                purchase_price_per_kg: parseFloat(price)
            }),
            credentials: 'include'
        });

        const responseText = await resp.text();
        console.log('Add new item response:', resp.status, responseText);
        
        if (resp.ok) {
            location.reload();
        } else {
            const error = await resp.text();
            alert("Error adding new item: " + error);
        }
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// ----------------- Sales Ledger -----------------
function downloadLedger() {
    window.location.href = '/api/admin/ledger/download';
}

// EXISTING FUNCTION: View sales for a specific item (kept as is)
async function viewItemSales(itemId) {
    try {
        const resp = await fetch(`/api/admin/sales/item/${itemId}`, {
            credentials: 'include'
        });
        if (!resp.ok) {
            const error = await resp.text();
            return alert("Error fetching sales: " + error);
        }

        const sales = await resp.json();
        let html = '';
        sales.forEach(s => {
            html += `<tr>
                <td>${s.sale_number}</td>
                <td>${s.item_name}</td>
                <td>${s.kg_sold}</td>
                <td>${s.price_per_kg_snapshot}</td>
                <td>${s.total_price}</td>
                <td>${s.cashier_name}</td>
                <td>${s.customer_name || '-'}</td>
                <td>${s.status}</td>
                <td>${s.created_at}</td>
            </tr>`;
        });

        document.getElementById('sales-ledger').innerHTML = html;
    } catch (err) {
        alert("Error: " + err.message);
    }
}

// EXISTING FUNCTION: Load all sales (kept as is)
async function loadAllSales() {
    try {
        const resp = await fetch('/api/admin/sales/all', {
            credentials: 'include'
        });
        if (!resp.ok) {
            alert("Error loading sales");
            return;
        }

        const sales = await resp.json();
        let html = '';
        sales.forEach(s => {
            html += `<tr>
                <td>${s.sale_number}</td>
                <td>${s.item_name}</td>
                <td>${s.kg_sold}</td>
                <td>${s.price_per_kg_snapshot}</td>
                <td>${s.total_price}</td>
                <td>${s.cashier_name}</td>
                <td>${s.customer_name || '-'}</td>
                <td>${s.status}</td>
                <td>${s.created_at}</td>
            </tr>`;
        });

        document.getElementById('sales-ledger').innerHTML = html;
        alert("Sales refreshed successfully!");
    } catch (err) {
        alert("Error: " + err.message);
    }
}