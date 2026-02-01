const itemSelect = document.getElementById('item');
const kgInput = document.getElementById('kg_sold');
const priceDisplay = document.getElementById('price_per_kg');
const totalDisplay = document.getElementById('total_price');
const form = document.getElementById('sale-form');
const recentSalesTbody = document.getElementById('recent-sales');

// Initialize price
function updateTotal() {
    const selectedOption = itemSelect.selectedOptions[0];
    const pricePerKg = parseFloat(selectedOption.dataset.price);
    const kgSold = parseFloat(kgInput.value) || 0;
    priceDisplay.textContent = pricePerKg.toFixed(2);
    totalDisplay.textContent = (pricePerKg * kgSold).toFixed(2);
}

itemSelect.addEventListener('change', updateTotal);
kgInput.addEventListener('input', updateTotal);
updateTotal(); // initial display

// Submit new sale
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const data = {
        item_id: parseInt(itemSelect.value),
        kg_sold: parseFloat(kgInput.value),
        payment_type: document.getElementById('payment_type').value,
        customer_name: document.getElementById('customer_name').value
    };

    try {
        const resp = await fetch('/sales', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        if (!resp.ok) throw new Error("Sale failed");

        const sale = await resp.json();

        // Append to recent sales table
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${sale.sale_number}</td>
            <td>${sale.item_name}</td>
            <td>${sale.kg_sold}</td>
            <td>${sale.total_price.toFixed(2)}</td>
            <td>${sale.created_at}</td>
        `;
        recentSalesTbody.prepend(tr);

        // Reset form
        form.reset();
        updateTotal();

    } catch (err) {
        alert(err.message);
    }
});

// Load recent sales on page load
async function loadRecentSales() {
    const resp = await fetch('/sales/recent');
    if (!resp.ok) return;
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
}

document.addEventListener('DOMContentLoaded', loadRecentSales);
