// PriceHunt — Main JS
// Handles: input animations, scroll effects, misc UX

document.addEventListener('DOMContentLoaded', () => {
    // Animate elements on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationPlayState = 'running';
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.product-card, .feature-card, .admin-stat-card').forEach(el => {
        el.style.animationPlayState = 'paused';
        observer.observe(el);
    });

    // Star rating widget
    document.querySelectorAll('.star-rating').forEach(widget => {
        const stars = widget.querySelectorAll('.star');
        const input = widget.querySelector('input[type=hidden]');
        stars.forEach((star, i) => {
            star.addEventListener('mouseenter', () => {
                stars.forEach((s, j) => s.classList.toggle('hover', j <= i));
            });
            star.addEventListener('mouseleave', () => {
                stars.forEach(s => s.classList.remove('hover'));
            });
            star.addEventListener('click', () => {
                const val = i + 1;
                if (input) input.value = val;
                stars.forEach((s, j) => s.classList.toggle('selected', j < val));
            });
        });
        widget.addEventListener('mouseleave', () => {
            stars.forEach(s => s.classList.remove('hover'));
        });
    });
});
