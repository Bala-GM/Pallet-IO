const palletInput = document.getElementById("palletNo");

palletInput.addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
        e.preventDefault();
        const value = palletInput.value.trim();
        if (value) scanPallet(value);
    }
});

function scanPallet(palletNo) {
    fetch("/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pallet_no: palletNo })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            updateTable(data.pallets);
            palletInput.value = "";
        } else {
            alert(data.message);
        }
        palletInput.focus();
    })
    .catch(err => console.error(err));
}

function updateTable(pallets) {
    const tbody = document.getElementById("palletTable");
    tbody.innerHTML = "";
    pallets.forEach(p => {
        const row = `<tr>
            <td>${p.id}</td>
            <td>${p.pallet_no}</td>
            <td>${p.out_time || ""}</td>
            <td>${p.in_time || ""}</td>
        </tr>`;
        tbody.insertAdjacentHTML("beforeend", row);
    });
}
