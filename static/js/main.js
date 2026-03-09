/* ============================================================
   Main JS — Face Recognition Attendance System
   ============================================================ */

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
    const flashes = document.querySelectorAll('.flash-msg');
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateX(100%)';
            setTimeout(() => flash.remove(), 500);
        }, 3500);

        // Click to dismiss
        flash.addEventListener('click', () => {
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 300);
        });
    });

    // Active nav highlight
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(item => {
        const href = item.getAttribute('href');
        if (href && (currentPath === href || (href !== '/admin/dashboard' && currentPath.startsWith(href)))) {
            item.classList.add('active');
        }
    });

    // Tables — live search
    const searchInputs = document.querySelectorAll('[data-search-table]');
    searchInputs.forEach(input => {
        const tableId = input.getAttribute('data-search-table');
        const table = document.getElementById(tableId);
        if (!table) return;

        input.addEventListener('input', () => {
            const term = input.value.toLowerCase();
            table.querySelectorAll('tbody tr').forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(term) ? '' : 'none';
            });
        });
    });

    // Animate elements into view
    const animEls = document.querySelectorAll('.animate-in');
    animEls.forEach((el, i) => {
        el.style.animationDelay = `${i * 0.06}s`;
    });
});

// ============================================================
// Webcam Utilities
// ============================================================
class WebcamManager {
    constructor(videoEl, canvasEl) {
        this.video = videoEl;
        this.canvas = canvasEl;
        this.stream = null;
        this.isRunning = false;
    }

    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
            });
            this.video.srcObject = this.stream;
            await this.video.play();
            this.isRunning = true;
            return true;
        } catch (e) {
            console.error('Camera error:', e);
            return false;
        }
    }

    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
            this.stream = null;
        }
        this.isRunning = false;
    }

    captureFrame(quality = 0.85) {
        if (!this.isRunning) return null;
        const ctx = this.canvas.getContext('2d');
        this.canvas.width = this.video.videoWidth || 640;
        this.canvas.height = this.video.videoHeight || 480;
        ctx.drawImage(this.video, 0, 0);
        return this.canvas.toDataURL('image/jpeg', quality);
    }
}

// ============================================================
// Show Notification Helper
function showNotification(message, type = 'info') {
    const container = document.querySelector('.flash-container') || (() => {
        const c = document.createElement('div');
        c.className = 'flash-container';
        document.body.appendChild(c);
        return c;
    })();

    const icons = {
        success: '<i data-lucide="check-circle" style="width:16px;height:16px;"></i>',
        danger: '<i data-lucide="alert-circle" style="width:16px;height:16px;"></i>',
        warning: '<i data-lucide="alert-triangle" style="width:16px;height:16px;"></i>',
        info: '<i data-lucide="info" style="width:16px;height:16px;"></i>'
    };
    const msg = document.createElement('div');
    msg.className = `flash-msg ${type}`;
    // Inline flex to align icon and text properly
    msg.style.display = 'flex';
    msg.style.alignItems = 'center';
    msg.style.gap = '8px';
    msg.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
    container.appendChild(msg);
    if (window.lucide) lucide.createIcons();

    setTimeout(() => {
        msg.style.animation = 'fadeOut 0.5s ease forwards';
        setTimeout(() => msg.remove(), 500);
    }, 3500);
}

// ============================================================
// Confirm dialog helper
// ============================================================
function confirmAction(message, callback) {
    if (window.confirm(message)) callback();
}

// ============================================================
// Delete employee with confirmation
// ============================================================
function deleteEmployee(employeeId, name) {
    if (confirm(`Are you sure you want to delete ${name}? This action cannot be undone.`)) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/admin/employees/delete/${employeeId}`;
        document.body.appendChild(form);
        form.submit();
    }
}

// ============================================================
// Dashboard stats auto-refresh
// ============================================================
function initDashboardRefresh() {
    const statsEl = {
        total: document.getElementById('stat-total'),
        present: document.getElementById('stat-present'),
        absent: document.getElementById('stat-absent'),
        rate: document.getElementById('stat-rate')
    };

    if (!statsEl.total) return;

    setInterval(async () => {
        try {
            const res = await fetch('/api/dashboard-stats');
            const data = await res.json();
            if (statsEl.total) statsEl.total.textContent = data.total_employees;
            if (statsEl.present) statsEl.present.textContent = data.present_today;
            if (statsEl.absent) statsEl.absent.textContent = data.absent_today;
            if (statsEl.rate) statsEl.rate.textContent = data.attendance_rate + '%';
        } catch (e) { /* silent */ }
    }, 30000); // Refresh every 30s
}

// ============================================================
// Chart.js Default Config
// ============================================================
function getChartDefaults() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: '#6B7280',
                    font: { family: 'Inter', size: 12 }
                }
            },
            tooltip: {
                backgroundColor: '#1F2937',
                borderColor: '#E2E8E6',
                borderWidth: 1,
                titleColor: '#FFFFFF',
                bodyColor: '#F3F4F6',
                padding: 10
            }
        }
    };
}

function createBarChart(ctx, labels, data, label = 'Attendance') {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: 'rgba(15, 118, 110, 0.85)',
                borderColor: '#0F766E',
                borderWidth: 1,
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            ...getChartDefaults(),
            scales: {
                y: {
                    ticks: { color: '#6B7280', font: { size: 11 } },
                    grid: { color: '#E5E7EB' },
                    border: { dash: [4, 4] }
                },
                x: {
                    ticks: { color: '#6B7280', font: { size: 11 } },
                    grid: { display: false }
                }
            }
        }
    });
}

function createLineChart(ctx, labels, data, label = 'Attendance') {
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: '#14B8A6',
                backgroundColor: 'rgba(20, 184, 166, 0.1)',
                borderWidth: 2,
                pointBackgroundColor: '#14B8A6',
                pointRadius: 4,
                pointHoverRadius: 6,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            ...getChartDefaults(),
            scales: {
                y: {
                    ticks: { color: '#6B7280', font: { size: 11 } },
                    grid: { color: '#E5E7EB' }
                },
                x: {
                    ticks: { color: '#6B7280', font: { size: 11 } },
                    grid: { display: false }
                }
            }
        }
    });
}

function createDoughnutChart(ctx, labels, data, colors) {
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors || ['#16A34A', '#DC2626'],
                borderColor: '#FFFFFF',
                borderWidth: 2,
                hoverOffset: 4
            }]
        },
        options: {
            ...getChartDefaults(),
            cutout: '75%'
        }
    });
}
