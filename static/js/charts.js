
const MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];

function renderIngresosChart() {
    const canvas = document.getElementById('grafico-ingresos');
    if (!canvas) return;

    const todosLosAños = JSON.parse(canvas.dataset.todos);
    const años = Object.keys(todosLosAños).map(Number).sort();
    let indiceActual = años.indexOf(parseInt(canvas.dataset.añoActual));
    if (indiceActual === -1) indiceActual = años.length - 1;

    let chartInstance = null;

    function mostrarAño(idx) {
        const año = años[idx];
        const ingresos = todosLosAños[año];
        const hayDatos = ingresos.some(v => v > 0);
        const total = ingresos.reduce((a, b) => a + b, 0);
        const totalEl = document.getElementById('total-año');
        if (totalEl) totalEl.textContent = '$' + total.toLocaleString('es-CL');

        document.getElementById('label-año').textContent = año;
        document.getElementById('btn-año-anterior').disabled = idx === 0;
        document.getElementById('btn-año-siguiente').disabled = idx === años.length - 1;

        const wrapper = document.getElementById('grafico-ingresos-wrapper');
        const vacio = document.getElementById('grafico-ingresos-vacio');

        if (!hayDatos) {
            wrapper.classList.add('d-none');
            vacio.classList.remove('d-none');
            if (chartInstance) { chartInstance.destroy(); chartInstance = null; }
            return;
        }

        wrapper.classList.remove('d-none');
        vacio.classList.add('d-none');

        if (chartInstance) chartInstance.destroy();


        const roundedMax = 2000000;
        const stepSize = 500000;

        const gradientPlugin = {
            id: 'gradientBars',
            afterLayout(chart) {
                const { ctx, chartArea: { top, bottom } } = chart;
                const gradient = ctx.createLinearGradient(0, top, 0, bottom);
                gradient.addColorStop(0, 'rgba(14, 76, 99, 0.35)');
                gradient.addColorStop(1, 'rgba(14, 76, 99, 1.0)');
                chart.data.datasets[0].backgroundColor = gradient;
            }
        };

        chartInstance = new Chart(canvas, {
            type: 'bar',
            plugins: [gradientPlugin],
            data: {
                labels: MESES_ES,
                datasets: [{
                    label: 'Ingreso Neto',
                    data: ingresos,
                    backgroundColor: 'rgba(14, 76, 99, 0.7)',
                    hoverBackgroundColor: 'rgba(14, 76, 99, 1.0)',
                    borderRadius: { topLeft: 4, topRight: 4 },
                    borderSkipped: 'bottom',
                    barPercentage: 0.7,
                    categoryPercentage: 0.75,
                }]
            },
            options: {
                animation: false,
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return ' $' + ctx.raw.toLocaleString('es-CL');
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        border: { display: false },
                        ticks: { color: '#aaa', font: { size: 11 } }
                    },
                    y: {
                        position: 'right',
                        min: 0,
                        max: roundedMax,
                        grid: { color: 'rgba(0,0,0,0.06)' },
                        border: { display: false },
                        ticks: {
                            stepSize: stepSize,
                            color: '#aaa',
                            font: { size: 11 },
                            callback: function (value) {
                                if (value === 0) return '$0';
                                if (value >= 1000000) return '$' + (value / 1000000).toFixed(1) + 'M';
                                return '$' + (value / 1000).toFixed(0) + 'K';
                            }
                        }
                    }
                }
            }
        });
    }

    // Inicializar
    mostrarAño(indiceActual);

    // Botones
    document.getElementById('btn-año-anterior').addEventListener('click', function () {
        if (indiceActual > 0) { indiceActual--; mostrarAño(indiceActual); }
    });
    document.getElementById('btn-año-siguiente').addEventListener('click', function () {
        if (indiceActual < años.length - 1) { indiceActual++; mostrarAño(indiceActual); }
    });
}



const COLORES_COMPARATIVO = [
    'rgba(14, 76, 99, 1.0)',
    'rgba(5, 150, 105, 1.0)',
    'rgba(217, 119, 6, 1.0)',
    'rgba(139, 92, 246, 1.0)',
];

function renderComparativoChart() {
    const canvas = document.getElementById('grafico-comparativo');
    if (!canvas) return;

    const instanciaAnterior = Chart.getChart(canvas);
    if (instanciaAnterior) instanciaAnterior.destroy();

    const comparativo = JSON.parse(canvas.dataset.comparativo);
    const años = Object.keys(comparativo).map(Number).sort();

    // Por defecto mostrar los últimos 2 años
    const añosActivos = años.slice(-2);

    function construirDatasets(añosMostrar) {
        const ordenados = [...añosMostrar].sort((a, b) => b - a); // más reciente primero
        return ordenados.map((anio, idx) => ({
            label: String(anio),
            data: comparativo[String(anio)],
            borderColor: COLORES_COMPARATIVO[idx % COLORES_COMPARATIVO.length],
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: COLORES_COMPARATIVO[idx % COLORES_COMPARATIVO.length],
            tension: 0.3,
        }));
    }

    const chart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: MESES_ES,
            datasets: construirDatasets(añosActivos),
        },
        options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return ' ' + ctx.dataset.label + ': $' + ctx.raw.toLocaleString('es-CL');
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    border: { display: false },
                    ticks: { color: '#aaa', font: { size: 11 } }
                },
                y: {
                    position: 'right',
                    min: 0,
                    grid: { color: 'rgba(0,0,0,0.06)' },
                    border: { display: false },
                    ticks: {
                        color: '#aaa',
                        font: { size: 11 },
                        callback: function (value) {
                            if (value >= 1000000) return '$' + (value / 1000000).toFixed(1) + 'M';
                            if (value >= 1000) return '$' + (value / 1000).toFixed(0) + 'K';
                            return '$' + value;
                        }
                    }
                }
            }
        }
    });

    // Selector de años
    document.querySelectorAll('.anio-check').forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            const seleccionados = Array.from(
                document.querySelectorAll('.anio-check:checked')
            ).map(cb => parseInt(cb.value)).sort();

            if (seleccionados.length === 0) return;

            chart.data.datasets = construirDatasets(seleccionados);
            chart.update('none');
        });
    });
}

function renderGaugeVelocimetro(canvasId, valor) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const inst = Chart.getChart(canvas);
    if (inst) inst.destroy();

    const ctx = canvas.getContext('2d');
    const cx = canvas.width / 2;
    const cy = canvas.height * 0.75;
    const radio = Math.min(canvas.width, canvas.height) * 0.42;

    // Fondo gris
    ctx.beginPath();
    ctx.arc(cx, cy, radio, Math.PI, 2 * Math.PI);
    ctx.strokeStyle = '#e9ecef';
    ctx.lineWidth = radio * 0.18;
    ctx.stroke();

    // Arco coloreado según valor
    const color = valor < 40 ? '#ef4444' : valor < 70 ? '#f59e0b' : '#0E4C63';
    const angulo = Math.PI + (valor / 100) * Math.PI;
    ctx.beginPath();
    ctx.arc(cx, cy, radio, Math.PI, angulo);
    ctx.strokeStyle = color;
    ctx.lineWidth = radio * 0.18;
    ctx.stroke();

    // Aguja
    const anguloAguja = Math.PI + (valor / 100) * Math.PI;
    const largoAguja = radio * 0.75;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(
        cx + largoAguja * Math.cos(anguloAguja),
        cy + largoAguja * Math.sin(anguloAguja)
    );
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Centro
    ctx.beginPath();
    ctx.arc(cx, cy, radio * 0.08, 0, 2 * Math.PI);
    ctx.fillStyle = '#374151';
    ctx.fill();
}

function renderOcupacionChart() {
    const card = document.getElementById('card-ocupacion-mes');
    if (!card) return;

    const todosMeses = JSON.parse(card.dataset.meses);
    const claves = Object.keys(todosMeses).sort().reverse(); // más reciente primero
    const MESES_NOMBRES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    let indiceActual = 0;

    function renderGauge(canvasId, valor) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const inst = Chart.getChart(canvas);
        if (inst) inst.destroy();

        const gradientPlugin = {
            id: 'gaugeGradient',
            afterLayout(chart) {
                const { ctx, chartArea } = chart;
                if (!chartArea) return;
                const gradient = ctx.createLinearGradient(
                    chartArea.left, chartArea.bottom,
                    chartArea.right, chartArea.top
                );
                gradient.addColorStop(0, 'rgba(14, 76, 99, 0.4)');
                gradient.addColorStop(1, 'rgba(14, 76, 99, 1.0)');
                chart.data.datasets[0].backgroundColor[0] = gradient;
            }
        };

        const chart = new Chart(canvas, {
            type: 'doughnut',
            plugins: [gradientPlugin],
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#0E4C63', '#e9ecef'],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270,
                }]
            },
            options: {
                animation: { duration: 800, easing: 'easeOutCubic' },
                responsive: true,
                maintainAspectRatio: true,
                cutout: '78%',
                events: [],
                plugins: { legend: { display: false }, tooltip: { enabled: false } }
            }
        });

        chart.data.datasets[0].data = [valor, 100 - valor];
        chart.update();
    }

    function mostrarMes(idx) {
        const clave = claves[idx];
        const datos = todosMeses[clave];

        document.getElementById('label-mes').textContent =
            `${MESES_NOMBRES[datos.mes - 1]} ${datos.anio}`;
        document.getElementById('btn-mes-anterior').disabled = idx === claves.length - 1;
        document.getElementById('btn-mes-siguiente').disabled = idx === 0;

        document.getElementById('label-pct-ocupacion').textContent = datos.ocupacion + '%';
        document.getElementById('stat-reservadas').textContent = datos.noches_reservadas;
        document.getElementById('stat-bloqueadas').textContent = datos.noches_bloqueadas;
        document.getElementById('stat-sinreserva').textContent = datos.noches_disponibles;
        document.getElementById('label-fds').textContent = datos.ocupacion_fds + '%';
        document.getElementById('label-semana').textContent = datos.ocupacion_semana + '%';

        renderGauge('gauge-ocupacion', datos.ocupacion);
        renderGauge('gauge-fds', datos.ocupacion_fds);
        renderGauge('gauge-semana', datos.ocupacion_semana);
    }

    mostrarMes(indiceActual);

    const btnAnterior = document.getElementById('btn-mes-anterior');
    const btnSiguiente = document.getElementById('btn-mes-siguiente');

    if (btnAnterior) {
        btnAnterior.addEventListener('click', function () {
            if (indiceActual < claves.length - 1) { indiceActual++; mostrarMes(indiceActual); }
        });
    }
    if (btnSiguiente) {
        btnSiguiente.addEventListener('click', function () {
            if (indiceActual > 0) { indiceActual--; mostrarMes(indiceActual); }
        });
    }

    // Comparativo
    const canvasComp = document.getElementById('grafico-ocupacion-comparativo');
    if (!canvasComp) return;

    const instComp = Chart.getChart(canvasComp);
    if (instComp) instComp.destroy();

    const comparativo = JSON.parse(canvasComp.dataset.comparativo);
    const anios = Object.keys(comparativo).map(Number).sort();
    const anioDefault = anios[anios.length - 1];

    function construirDatasetsOcupacion(aniosMostrar) {
        return [...aniosMostrar].sort((a, b) => b - a).map((anio, idx) => ({
            label: String(anio),
            data: comparativo[String(anio)],
            borderColor: COLORES_COMPARATIVO[idx % COLORES_COMPARATIVO.length],
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: COLORES_COMPARATIVO[idx % COLORES_COMPARATIVO.length],
            tension: 0.3,
        }));
    }

    function actualizarTotales(aniosMostrar) {
        const contenedor = document.getElementById('totales-ocupacion');
        if (!contenedor) return;
        contenedor.innerHTML = [...aniosMostrar].sort((a, b) => b - a).map((anio, idx) => {
            const datos = comparativo[String(anio)];
            const mesesConDias = [31, (anio % 4 === 0 ? 29 : 28), 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
            const diasAnio = mesesConDias.reduce((a, b) => a + b, 0);
            const nochesOcupadas = datos.reduce((sum, pct, i) => sum + (pct / 100 * mesesConDias[i]), 0);
            const ocupacionAnual = (nochesOcupadas / diasAnio * 100).toFixed(1);
            return `
                <div class="px-4 py-2 rounded-3 text-center" style="background:rgba(14,76,99,0.06);">
                    <div class="text-muted mb-1" style="font-size:0.75rem;letter-spacing:0.05em;text-transform:uppercase;">
                        Ocupación ${anio}
                    </div>
                    <div class="fw-bold" style="font-size:1.3rem;color:${COLORES_COMPARATIVO[idx]};">${ocupacionAnual}%</div>
                </div>`;
        }).join('');
    }

    const chart = new Chart(canvasComp, {
        type: 'line',
        data: { labels: MESES_ES, datasets: construirDatasetsOcupacion([anioDefault]) },
        options: {
            animation: false,
            responsive: true,
            maintainAspectRatio: false,
            clip: false, // ← permite que los puntos se dibujen fuera del área
            plugins: {
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return ' ' + ctx.dataset.label + ': ' + ctx.raw + '%';
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false }, border: { display: false }, ticks: { color: '#aaa', font: { size: 11 } } },
                y: {
                    position: 'right', min: 0, max: 100,
                    grid: { color: 'rgba(0,0,0,0.06)' }, border: { display: false },
                    ticks: { stepSize: 25, color: '#aaa', font: { size: 11 }, callback: v => v + '%' }
                }
            }
        }
    });

    actualizarTotales([anioDefault]);

    document.querySelectorAll('.anio-check-ocupacion').forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            const seleccionados = Array.from(
                document.querySelectorAll('.anio-check-ocupacion:checked')
            ).map(cb => parseInt(cb.value)).sort();
            if (seleccionados.length === 0) return;
            chart.data.datasets = construirDatasetsOcupacion(seleccionados);
            chart.update('none');
            actualizarTotales(seleccionados);
        });
    });
}