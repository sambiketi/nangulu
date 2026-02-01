// ----------------- Cashiers -----------------
async function addCashier() {
    const username = prompt("Enter cashier username:");
    const fullName = prompt("Enter full name:");
    const password = prompt("Enter password:");

    if (!username || !fullName || !password) return alert("All fields are required");

    const resp = await fetch('/cashiers', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, full_name: fullName, password})
    });

    if (resp.ok) location.reload();
    else alert("Error adding cashier");
}

// ----------------- Inventory -----------------
async function setPrice(itemId) {
    const input = document.querySelector(`input[data-id='${itemId}']`);
    const price = parseFloat(input.value);
    if (isNaN(price)) return alert("Invalid price");

    const resp = await fetch(`/inventory/${itemId}/set-price`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({current_price_per_kg: price})
    });

    if (resp.ok) location.reload();
    else alert("Error updating price");
}

async function addPurchase(itemId) {
    const qty = prompt("Enter quantity to add (kg):");
    if (!qty || isNaN(qty)) return alert("Invalid quantity");

    const resp = await fetch(`/inventory/${itemId}/add-stock`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({kg_added: parseFloat(qty)})
    });

    if (resp.ok) location.reload();
    else alert("Error adding stock");
}

// ----------------- Sales Ledger -----------------
function downloadLedger() {
    window.location.href = '/ledger/download';
}

// View sales for a specific item
async function viewItemSales(itemId) {
    const resp = await fetch(`/sales/item/${itemId}`);
    if (!resp.ok) return alert("Error fetching sales");

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
}
