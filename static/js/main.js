function toggleMenu() {

    const nav = document.querySelector(".nav-links");

    if (!nav) {
        return;
    }

    if (nav.style.display === "flex") {
        nav.style.display = "";
    } else {
        nav.style.display = "flex";
        nav.style.flexDirection = "column";
        nav.style.position = "absolute";
        nav.style.top = "78px";
        nav.style.left = "0";
        nav.style.right = "0";
        nav.style.padding = "25px";
        nav.style.background = "#081827";
        nav.style.borderBottom = "1px solid rgba(255,255,255,0.08)";
    }
}