/**
 * SMART BI — FEATURES INTERACTIVE ENGINE
 * File: static/js/features.js
 * Vanilla JavaScript implementation for scroll reveals, sticky layer
 * nav synchronization, tower node animation, What-If demo calculations,
 * and smooth link routing.
 */

document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  const rootEl = document.getElementById("smartFeaturesRoot");
  if (!rootEl) return;

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ==========================================================================
     1. SCROLL REVEAL OBSERVER
     ========================================================================== */
  const initScrollReveal = () => {
    const revealElements = rootEl.querySelectorAll(".feat-reveal");
    if (!revealElements.length) return;

    if (prefersReducedMotion) {
      revealElements.forEach((el) => el.classList.add("revealed"));
      return;
    }

    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          obs.unobserve(entry.target);
        }
      });
    }, {
      root: null,
      threshold: 0.12,
      rootMargin: "0px 0px -50px 0px",
    });

    revealElements.forEach((el) => observer.observe(el));
  };

  /* ==========================================================================
     2. STICKY QUICK-NAV & LAYER INTERSECTION SYNCHRONIZATION
     ========================================================================== */
  const initLayerNavSync = () => {
    const navLinks = rootEl.querySelectorAll(".feat-nav-link");
    const layerSections = [
      document.getElementById("layerData"),
      document.getElementById("layerAnalytics"),
      document.getElementById("layerInsights"),
      document.getElementById("layerDecisions"),
      document.getElementById("layerReporting")
    ].filter(Boolean);

    if (!navLinks.length || !layerSections.length) return;

    // Smooth click handler
    navLinks.forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const targetId = link.getAttribute("data-layer-target");
        const targetSec = document.getElementById(targetId);
        if (targetSec) {
          const offsetTop = targetSec.getBoundingClientRect().top + window.pageYOffset - 90;
          window.scrollTo({ top: offsetTop, behavior: "smooth" });
        }
      });
    });

    // Intersection observer for active navigation state
    const layerObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const currentId = entry.target.id;
          navLinks.forEach((link) => {
            if (link.getAttribute("data-layer-target") === currentId) {
              link.classList.add("active");
            } else {
              link.classList.remove("active");
            }
          });
        }
      });
    }, {
      root: null,
      threshold: 0.35,
      rootMargin: "-80px 0px -40% 0px"
    });

    layerSections.forEach((sec) => layerObserver.observe(sec));
  };

  /* ==========================================================================
     3. HERO TOWER NODES STEPPING CYCLER
     ========================================================================== */
  const initTowerCycler = () => {
    const towerNodes = rootEl.querySelectorAll(".feat-tower-node");
    if (!towerNodes.length || prefersReducedMotion) return;

    let activeStage = 0;
    const totalStages = towerNodes.length;

    setInterval(() => {
      towerNodes.forEach((node) => node.classList.remove("active"));
      towerNodes[activeStage].classList.add("active");
      activeStage = (activeStage + 1) % totalStages;
    }, 2000);
  };

  /* ==========================================================================
     4. WHAT-IF SCENARIO DEMO SIMULATOR
     ========================================================================== */
  const initWhatIfDemo = () => {
    const priceSlider = document.getElementById("priceSlider");
    const mktgSlider = document.getElementById("mktgSpendSlider");
    const priceDisplay = document.getElementById("priceDisplay");
    const mktgDisplay = document.getElementById("mktgDisplay");
    const resultRevenue = document.getElementById("simResultRevenue");
    const resultProfit = document.getElementById("simResultProfit");

    if (!priceSlider || !mktgSlider || !resultRevenue || !resultProfit) return;

    const baseRevenue = 12.8; // Base in Millions
    const baseProfit = 3.4;   // Base in Millions

    const updateSimulation = () => {
      const priceVal = parseFloat(priceSlider.value);
      const mktgVal = parseFloat(mktgSlider.value);

      priceDisplay.textContent = `${priceVal >= 0 ? "+" : ""}${priceVal}%`;
      mktgDisplay.textContent = `${mktgVal >= 0 ? "+" : ""}${mktgVal}%`;

      // Demonstrative calculation model (Illustrative Sandbox)
      const revenueGrowth = (priceVal * 0.65) + (mktgVal * 0.42);
      const profitGrowth = (priceVal * 0.85) + (mktgVal * 0.28);

      const projectedRev = baseRevenue * (1 + revenueGrowth / 100);
      const projectedProf = baseProfit * (1 + profitGrowth / 100);

      resultRevenue.textContent = `₹${projectedRev.toFixed(1)}M`;
      resultProfit.textContent = `₹${projectedProf.toFixed(1)}M`;
    };

    priceSlider.addEventListener("input", updateSimulation);
    mktgSlider.addEventListener("input", updateSimulation);
  };

  /* ==========================================================================
     5. SMOOTH SCROLL ROUTER FOR "EXPLORE FEATURES"
     ========================================================================== */
  const initSmoothScrollCTA = () => {
    const exploreBtn = document.getElementById("exploreFeaturesBtn");
    if (!exploreBtn) return;

    exploreBtn.addEventListener("click", (e) => {
      e.preventDefault();
      const targetSec = document.getElementById("featureArchitecture");
      if (targetSec) {
        targetSec.scrollIntoView({ behavior: "smooth" });
      }
    });
  };

  // Initialize all modular controllers
  initScrollReveal();
  initLayerNavSync();
  initTowerCycler();
  initWhatIfDemo();
  initSmoothScrollCTA();
});