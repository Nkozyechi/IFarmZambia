/**
 * IFarm Zambia - Main JavaScript
 * Interactive UI logic and utilities
 */

// ── Sidebar Toggle ──────────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', function(e) {
    const sidebar = document.getElementById('sidebar');
    const toggle = document.querySelector('.menu-toggle');
    
    if (window.innerWidth <= 768 && sidebar && !sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
    }
});

// ── Number Animation ────────────────────────────────────────────
function animateValue(element, start, end, duration) {
    const range = end - start;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        
        const current = start + range * eased;
        
        if (element.dataset.format === 'price') {
            element.textContent = 'ZMW ' + current.toFixed(2);
        } else if (element.dataset.format === 'percent') {
            element.textContent = current.toFixed(1) + '%';
        } else {
            element.textContent = Math.round(current);
        }
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// ── Intersection Observer for Animations ────────────────────────
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

document.addEventListener('DOMContentLoaded', function() {
    // Observe cards for animation
    document.querySelectorAll('.stat-card, .crop-card, .metric-card, .chart-card').forEach(function(el) {
        observer.observe(el);
    });
    
    // Auto-select crop from URL params
    const params = new URLSearchParams(window.location.search);
    const cropParam = params.get('crop');
    if (cropParam) {
        const select = document.getElementById('crop_id');
        if (select) {
            select.value = cropParam;
        }
    }
});

// ── Chart.js Default Config ─────────────────────────────────────
if (typeof Chart !== 'undefined') {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(148, 163, 184, 0.1)';
    Chart.defaults.font.family = "'Inter', sans-serif";
}
