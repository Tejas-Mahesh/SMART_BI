document.addEventListener("DOMContentLoaded", function () {

    const sidebar =
        document.getElementById("workspaceSidebar");

    const menuButton =
        document.getElementById("workspaceMenuButton");

    const overlay =
        document.getElementById("workspaceOverlay");


    function openSidebar() {

        if (!sidebar) {
            return;
        }

        sidebar.classList.add("mobile-open");

        if (overlay) {
            overlay.classList.add("active");
        }

        document.body.style.overflow = "hidden";

    }


    function closeSidebar() {

        if (!sidebar) {
            return;
        }

        sidebar.classList.remove("mobile-open");

        if (overlay) {
            overlay.classList.remove("active");
        }

        document.body.style.overflow = "";

    }


    if (menuButton) {

        menuButton.addEventListener(
            "click",
            function () {

                if (
                    sidebar &&
                    sidebar.classList.contains("mobile-open")
                ) {

                    closeSidebar();

                } else {

                    openSidebar();

                }

            }
        );

    }


    if (overlay) {

        overlay.addEventListener(
            "click",
            closeSidebar
        );

    }


    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Escape") {
                closeSidebar();
            }

        }
    );


    const comingSoonLinks =
        document.querySelectorAll(
            ".workspace-coming-soon"
        );


    comingSoonLinks.forEach(function (link) {

        link.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

            }
        );

    });

});