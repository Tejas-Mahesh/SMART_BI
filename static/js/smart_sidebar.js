/* =========================================================
   SMART BI SIDEBAR
   - Mobile open / close
   - Collapsible sections
   - Auto-open active section
   - Close sidebar after mobile navigation
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const sidebar =
        document.getElementById("smartBISidebar");

    const toggleButton =
        document.getElementById("mobileSidebarToggle");

    const overlay =
        document.getElementById("sidebarOverlay");


    if (!sidebar) {
        return;
    }


    /* =====================================================
       MOBILE SIDEBAR
    ====================================================== */

    function openMobileSidebar() {

        sidebar.classList.add("sidebar-open");

        document.body.classList.add(
            "sidebar-mobile-open"
        );

        if (toggleButton) {

            toggleButton.classList.add(
                "is-open"
            );

            toggleButton.setAttribute(
                "aria-expanded",
                "true"
            );

        }

        if (overlay) {
            overlay.classList.add("show");
        }

    }


    function closeMobileSidebar() {

        sidebar.classList.remove(
            "sidebar-open"
        );

        document.body.classList.remove(
            "sidebar-mobile-open"
        );

        if (toggleButton) {

            toggleButton.classList.remove(
                "is-open"
            );

            toggleButton.setAttribute(
                "aria-expanded",
                "false"
            );

        }

        if (overlay) {
            overlay.classList.remove("show");
        }

    }


    function toggleMobileSidebar() {

        if (
            sidebar.classList.contains(
                "sidebar-open"
            )
        ) {

            closeMobileSidebar();

        } else {

            openMobileSidebar();

        }

    }


    if (toggleButton) {

        toggleButton.addEventListener(
            "click",
            toggleMobileSidebar
        );

    }


    if (overlay) {

        overlay.addEventListener(
            "click",
            closeMobileSidebar
        );

    }


    /* =====================================================
       ESC KEY
    ====================================================== */

    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Escape") {

                closeMobileSidebar();

            }

        }
    );


    /* =====================================================
       COLLAPSIBLE SIDEBAR SECTIONS
    ====================================================== */

    const sectionButtons =
        document.querySelectorAll(
            "[data-toggle-section]"
        );


    sectionButtons.forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                const sectionName =
                    button.getAttribute(
                        "data-toggle-section"
                    );

                const section =
                    document.querySelector(
                        '[data-section="' +
                        sectionName +
                        '"]'
                    );


                if (!section) {
                    return;
                }


                const isOpen =
                    section.classList.contains(
                        "section-open"
                    );


                /*
                   Optional accordion behavior:
                   only one large section stays open.
                */

                document
                    .querySelectorAll(
                        ".sidebar-collapsible"
                    )
                    .forEach(function (otherSection) {

                        if (
                            otherSection !== section
                        ) {

                            otherSection.classList.remove(
                                "section-open"
                            );

                            const otherButton =
                                otherSection.querySelector(
                                    ".sidebar-group-button"
                                );

                            if (otherButton) {

                                otherButton.setAttribute(
                                    "aria-expanded",
                                    "false"
                                );

                            }

                        }

                    });


                if (isOpen) {

                    section.classList.remove(
                        "section-open"
                    );

                    button.setAttribute(
                        "aria-expanded",
                        "false"
                    );

                } else {

                    section.classList.add(
                        "section-open"
                    );

                    button.setAttribute(
                        "aria-expanded",
                        "true"
                    );

                }

            }
        );

    });


    /* =====================================================
       MOBILE NAVIGATION CLOSE
    ====================================================== */

    const navigationLinks =
        sidebar.querySelectorAll(
            "a.sidebar-link"
        );


    navigationLinks.forEach(function (link) {

        link.addEventListener(
            "click",
            function () {

                if (
                    window.innerWidth <= 700
                ) {

                    closeMobileSidebar();

                }

            }
        );

    });


    /* =====================================================
       RESIZE HANDLER
    ====================================================== */

    window.addEventListener(
        "resize",
        function () {

            if (
                window.innerWidth > 700
            ) {

                closeMobileSidebar();

            }

        }
    );

});