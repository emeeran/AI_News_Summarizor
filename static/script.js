// Script to add interactive features (if needed)

// Smooth scroll to the top when refreshing
document.addEventListener('DOMContentLoaded', function () {
    window.scrollTo(0, 0);
});

// Lazy load for images
document.addEventListener("DOMContentLoaded", function () {
    const lazyImages = document.querySelectorAll("img[loading='lazy']");

    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const image = entry.target;
                image.src = image.dataset.src;
                image.removeAttribute("loading");
                observer.unobserve(image);
            }
        });
    });

    lazyImages.forEach(image => {
        imageObserver.observe(image);
    });
});
