// PriceHunt — Main JS
// Handles: cart updates, scroll animations, star ratings

document.addEventListener('DOMContentLoaded', () => {
    // 1. Cap nhat so luong gio hang ngay khi trang vua tai xong
    updateCartBadge();

    // 2. Animate elements on scroll (Hieu ung hien thi khi cuon chuot)
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

    // 3. Star rating widget (Logic cho phan danh gia sao)
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

/**
 * Ham lay so luong gio hang tu server va hien thi len Badge
 * Dung chung cho tat ca cac trang (Index, History, Cart, Orders)
 */
function updateCartBadge() {
    const el = document.getElementById('cart-count');
    if (el) {
        fetch('/cart/count')
            .then(r => {
                if (!r.ok) throw new Error('Network response was not ok');
                return r.json();
            })
            .then(d => {
                // Neu co du lieu thi hien, khong thi hien 0
                el.textContent = (d.count !== undefined && d.count !== null) ? d.count : 0;
            })
            .catch(err => {
                console.error("Loi khi cap nhat gio hang:", err);
                el.textContent = '0';
            });
    }
}