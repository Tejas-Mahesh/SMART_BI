/**
 * SMART BI — ENTERPRISE SIDEBAR CONTROLLER
 * File: static/js/smart-sidebar.js
 * High-performance vanilla JavaScript controller managing:
 * - Mobile slide-in drawer state and backdrop overlay
 * - Collapsible section state toggling with aria-expanded sync
 * - Mobile navigation auto-closing & keyboard accessibility (Escape to close)
 * - Preservation of server-rendered active states
 */

document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  const sidebar = document.getElementById("smartBISidebar");
  const toggleBtn = document.getElementById("mobileSidebarToggle");
  const overlay = document.getElementById("sidebarOverlay");
  const collapsibleSections = document.querySelectorAll(".sidebar-collapsible");

  /* ==========================================================================
     1. MOBILE SIDEBAR OPEN / CLOSE HANDLERS
     ========================================================================== */
  const openSidebar = () => {
    if (!sidebar) return;
    sidebar.classList.add("sidebar-open");
    if (overlay) overlay.classList.add("active");
    if (toggleBtn) {
      toggleBtn.classList.add("open");
      toggleBtn.setAttribute("aria-expanded", "true");
    }
    document.body.classList.add("sidebar-open");
  };

  const closeSidebar = () => {
    if (!sidebar) return;
    sidebar.classList.remove("sidebar-open");
    if (overlay) overlay.classList.remove("active");
    if (toggleBtn) {
      toggleBtn.classList.remove("open");
      toggleBtn.setAttribute("aria-expanded", "false");
    }
    document.body.classList.remove("sidebar-open");
  };

  const toggleSidebar = () => {
    if (!sidebar) return;
    const isOpen = sidebar.classList.contains("sidebar-open");
    if (isOpen) {
      closeSidebar();
    } else {
      openSidebar();
    }
  };

  if (toggleBtn) {
    toggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleSidebar();
    });
  }

  if (overlay) {
    overlay.addEventListener("click", () => {
      closeSidebar();
    });
  }

  // Keyboard navigation: Escape key closes sidebar
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar && sidebar.classList.contains("sidebar-open")) {
      closeSidebar();
      if (toggleBtn) toggleBtn.focus();
    }
  });

  // Mobile Link Click: Automatically close sidebar so navigation feels snappy
  if (sidebar) {
    const navLinks = sidebar.querySelectorAll(".sidebar-link:not(.sidebar-settings-link)");
    navLinks.forEach((link) => {
      link.addEventListener("click", () => {
        if (window.innerWidth <= 1024) {
          closeSidebar();
        }
      });
    });
  }

  /* ==========================================================================
     2. COLLAPSIBLE ACCORDION SECTIONS
     ========================================================================== */
  collapsibleSections.forEach((section) => {
    const trigger = section.querySelector(".sidebar-group-button");
    const content = section.querySelector(".sidebar-group-content");

    // Preserve initial server-rendered state
    const isInitiallyOpen = section.classList.contains("section-open");
    if (trigger) {
      trigger.setAttribute("aria-expanded", isInitiallyOpen ? "true" : "false");
    }

    if (trigger) {
      trigger.addEventListener("click", (e) => {
        e.preventDefault();
        const isOpen = section.classList.contains("section-open");

        if (isOpen) {
          section.classList.remove("section-open");
          trigger.setAttribute("aria-expanded", "false");
        } else {
          section.classList.add("section-open");
          trigger.setAttribute("aria-expanded", "true");
        }
      });
    }
  });

  /* ==========================================================================
     3. PREVENT UNNECESSARY BEHAVIOR ON DISABLED/SETTINGS LINKS
     ========================================================================== */
  const settingsLinks = document.querySelectorAll(".sidebar-settings-link");
  settingsLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
    });
  });

  /* ==========================================================================
     4. RESIZE EVENT WATCHER
     ========================================================================== */
  window.addEventListener("resize", () => {
    if (window.innerWidth > 1024 && sidebar && sidebar.classList.contains("sidebar-open")) {
      closeSidebar();
    }
  }, { passive: true });
});