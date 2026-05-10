function toggleMenu() {
    const nav = document.getElementById('navLinks');
    nav.classList.toggle('open');
}

// Auto-dismiss flash messages after 4s
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        document.querySelectorAll('.flash').forEach(el => {
            el.style.transition = 'opacity 0.5s';
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 500);
        });
    }, 4000);

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        const nav = document.getElementById('navLinks');
        const toggle = document.querySelector('.menu-toggle');
        if (nav && !nav.contains(e.target) && !toggle.contains(e.target)) {
            nav.classList.remove('open');
        }
    });
});
