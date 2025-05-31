function updateSummary() {
    const prices = {
        festival: 3220000,
        cat2: 2702500,
        cat3: 2242500,
        cat4: 1552500
    };

    let totalTickets = 0;
    let subtotal = 0;

    for (let key in prices) {
        const qty = parseInt(document.getElementById(key).value) || 0;
        totalTickets += qty;
        subtotal += qty * prices[key];
    }

    document.getElementById("ticketCount").textContent = totalTickets;
    document.getElementById("subtotal").textContent = subtotal.toLocaleString("id-ID");
}