document.addEventListener("DOMContentLoaded", () => {

    /* ============================================
       SCROLL REVEAL
    ============================================ */

    const revealElements =
        document.querySelectorAll(".reveal");

    const revealObserver =
        new IntersectionObserver(
            (entries) => {

                entries.forEach((entry) => {

                    if (entry.isIntersecting) {

                        entry.target.classList.add("visible");

                        revealObserver.unobserve(
                            entry.target
                        );

                    }

                });

            },
            {
                threshold: 0.12
            }
        );


    revealElements.forEach((element) => {
        revealObserver.observe(element);
    });


    /* ============================================
       DASHBOARD PARALLAX
    ============================================ */

    const dashboard =
        document.querySelector(".hero-dashboard");

    if (dashboard && window.innerWidth > 900) {

        document.addEventListener("mousemove", (event) => {

            const x =
                (event.clientX / window.innerWidth - 0.5);

            const y =
                (event.clientY / window.innerHeight - 0.5);

            dashboard.style.transform =
                `translate(${x * 8}px, ${y * 8}px)`;

        });

    }


    /* ============================================
       KPI HOVER TRANSFORMATION
    ============================================ */

    const cards =
        document.querySelectorAll(
            ".capability-card, .flow-card, .mini-kpi"
        );


    cards.forEach((card) => {

        card.addEventListener("mouseenter", () => {
            card.style.willChange = "transform";
        });

        card.addEventListener("mouseleave", () => {
            card.style.willChange = "auto";
        });

    });


    /* ============================================
       SMOOTH INTERNAL NAVIGATION
    ============================================ */

    document.querySelectorAll(
        'a[href^="#"]'
    ).forEach((link) => {

        link.addEventListener("click", (event) => {

            const target =
                document.querySelector(
                    link.getAttribute("href")
                );

            if (!target) return;

            event.preventDefault();

            target.scrollIntoView({
                behavior: "smooth"
            });

        });

    });

});