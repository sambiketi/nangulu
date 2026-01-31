// -----------------------------
// Cashier Dashboard JS
// -----------------------------

async function confirmSale(itemId) {
    let kg = prompt("Enter kg sold:");
    let paymentType = prompt("Payment type (Cash / Mpesa):", "Cash");
    if (!kg) return;

    const response = await fetch("/api/cashier/sales", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_id: itemId, kg_sold: parseFloat(kg), payment_type: paymentType })
    });

    const data = await response.json();
    if (data.detail) {
        alert("Error: " + data.detail);
    } else {
        alert(`Sale confirmed! Total price: ${data.total_price}`);
        location.reload(); // Refresh dashboard
    }
}

async function reverseSale(saleId) {
    if (!confirm("Are you sure you want to reverse this sale?")) return;

    const response = await fetch(`/api/cashier/sales/${saleId}/reverse`, { method: "POST" });
    const data = await response.json();

    if (data.detail) {
        alert("Error: " + data.detail);
    } else {
        alert(`Sale ${data.sale_number} reversed`);
        location.reload();
    }
}

// -----------------------------
// Admin Dashboard JS
// -----------------------------

async function addCashier() {
    const username = prompt("Username:");
    const fullName = prompt("Full Name:");
    const password = prompt("Password:");

    const response = await fetch("/api/admin/cashiers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username, full_name: fullName, role: "cashier", password: password })
    });

    const data = await response.json();
    if (data.detail) alert("Error: " + data.detail);
    else location.reload();
}

async function addPurchase(itemId=null) {
    const kg = parseFloat(prompt("Quantity in kg:"));
    const price = parseFloat(prompt("Purchase price per kg:"));
    const name = itemId ? null : prompt("New item name:");
    const description = itemId ? null : prompt("Description:");

    const body = { kg_added: kg, purchase_price_per_kg: price };
    if (itemId) body.item_id = itemId;
    else { body.name = name; body.description = description; }

    const response = await fetch("/api/admin/purchases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });

    const data = await response.json();
    if (data.detail) alert("Error: " + data.detail);
    else location.reload();
}

async function setPrice(itemId) {
    const price = parseFloat(prompt("New selling price per kg:"));
    const response = await fetch(`/api/admin/inventory/${itemId}/price?price=${price}`, { method: "PATCH" });
    const data = await response.json();
    if (data.detail) alert("Error: " + data.detail);
    else location.reload();
}

function downloadLedger() {
    window.location.href = "/api/admin/ledger/download";
}
