document.addEventListener('DOMContentLoaded', function () {

    const listingEl = document.getElementById('id_listing');
    const bookingEl = document.getElementById('id_booking');
    const typeEl = document.getElementById('id_transaction_type');
    const categoryEl = document.getElementById('id_category');
    const impactEl = document.getElementById('id_owner_impact');
    const dateEl = document.getElementById('id_transaction_date');

    // ── 1. Fecha por defecto: hoy ──
    if (dateEl && !dateEl.value) {
        const hoy = new Date();
        const yyyy = hoy.getFullYear();
        const mm = String(hoy.getMonth() + 1).padStart(2, '0');
        const dd = String(hoy.getDate()).padStart(2, '0');
        dateEl.value = `${yyyy}-${mm}-${dd}`;
    }

    // ── 2. Al cambiar listing: filtrar bookings por propiedad ──
    if (listingEl && bookingEl) {
        listingEl.addEventListener('change', function () {
            const listingId = this.value;
            if (!listingId) return;

            fetch(`/api/bookings-por-propiedad/?listing_id=${listingId}`)
                .then(r => r.json())
                .then(data => {
                    bookingEl.innerHTML = '<option value="">---------</option>';
                    data.forEach(b => {
                        const opt = document.createElement('option');
                        opt.value = b.id;
                        opt.textContent = b.label;
                        bookingEl.appendChild(opt);
                    });
                });
        });
    }

    // ── 3. Al cambiar transaction_type: filtrar categorías ──
    const incomeCats = ['late_checkout', 'early_checkin', 'additional_night', 'cleaning', 'other'];
    const expenseCats = ['repair', 'supply', 'guest_compensation', 'maintenance', 'other'];

    function filtrarCategorias() {
        if (!typeEl || !categoryEl) return;
        const tipo = typeEl.value;
        const permitidas = tipo === 'income' ? incomeCats : expenseCats;

        Array.from(categoryEl.options).forEach(opt => {
            if (opt.value === '') return; // mantener el "---"
            opt.hidden = !permitidas.includes(opt.value);
        });

        // Si la categoría actual quedó oculta, resetear
        if (categoryEl.value && !permitidas.includes(categoryEl.value)) {
            categoryEl.value = '';
        }
        actualizarImpacto();
    }

    if (typeEl) typeEl.addEventListener('change', filtrarCategorias);

    // ── 4. Al cambiar categoría: forzar owner_impact si late/early ──
    function actualizarImpacto() {
        if (!categoryEl || !impactEl) return;
        const cat = categoryEl.value;

        if (['late_checkout', 'early_checkin', 'additional_night'].includes(cat)) {
            impactEl.value = 'mixed';
            impactEl.style.pointerEvents = 'none';
            impactEl.style.opacity = '0.6';
        } else if (cat === 'cleaning') {
            impactEl.value = 'full_owner';
            impactEl.style.pointerEvents = 'none';
            impactEl.style.opacity = '0.6';
        } else {
            impactEl.style.pointerEvents = '';
            impactEl.style.opacity = '';
        }
    }

    if (categoryEl) categoryEl.addEventListener('change', actualizarImpacto);

    // Correr al cargar por si hay valores previos
    filtrarCategorias();
    actualizarImpacto();
});