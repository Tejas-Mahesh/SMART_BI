/**
 * SMART BI — HOW IT WORKS INTERACTIVE SCRIPT
 * File: static/js/how_it_works.js
 * Vanilla JavaScript implementation for scroll reveal, timeline tracers,
 * continuous hero node animation, What-If simulator elasticity logic,
 * canvas particle flow, and smooth navigation.
 */

document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  const rootEl = document.getElementById("smartHowItWorks");
  if (!rootEl) return;

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ==========================================================================
     1. SCROLL REVEAL OBSERVER
     ========================================================================== */
  const initScrollReveal = () => {
    const reveals = rootEl.querySelectorAll(".how-reveal");
    if (!reveals.length) return;

    if (prefersReducedMotion) {
      reveals.forEach((el) => el.classList.add("revealed"));
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

    reveals.forEach((el) => observer.observe(el));
  };

  /* ==========================================================================
     2. WORKFLOW TIMELINE TRACER & STEP ACTIVATION
     ========================================================================== */
  const initTimelineObserver = () => {
    const stepRows = rootEl.querySelectorAll(".workflow-step-row");
    const tracer = document.getElementById("howSpineTracer");
    const container = document.getElementById("howTimelineContainer");

    if (!stepRows.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          stepRows.forEach((row) => row.classList.remove("active"));
          entry.target.classList.add("active");

          if (tracer && container && !prefersReducedMotion) {
            const containerRect = container.getBoundingClientRect();
            const beacon = entry.target.querySelector(".workflow-timeline-beacon");
            if (beacon) {
              const beaconRect = beacon.getBoundingClientRect();
              const relativeTop = beaconRect.top - containerRect.top;
              tracer.style.top = `${Math.max(0, relativeTop - 30)}px`;
            }
          }
        }
      });
    }, {
      root: null,
      threshold: 0.4,
      rootMargin: "0px 0px -20% 0px",
    });

    stepRows.forEach((row) => observer.observe(row));
  };

  /* ==========================================================================
     3. HERO PIPELINE CIRCUIT NODES CONTINUOUS CYCLER
     ========================================================================== */
  const initHeroPipelineCycler = () => {
    const circuitNodes = rootEl.querySelectorAll(".how-circuit-node");
    if (!circuitNodes.length || prefersReducedMotion) return;

    let activeIdx = 0;
    const total = circuitNodes.length;

    setInterval(() => {
      circuitNodes.forEach((node) => node.classList.remove("active"));
      circuitNodes[activeIdx].classList.add("active");
      activeIdx = (activeIdx + 1) % total;
    }, 1800);
  };

  /* ==========================================================================
     4. WHAT-IF SCENARIO SIMULATOR (STEP 4 REACTIVE LOGIC)
     ========================================================================== */
  const initWhatIfSimulator = () => {
    const mktgSlider = document.getElementById("marketingSlider");
    const demandSlider = document.getElementById("demandSlider");
    const mktgValDisp = document.getElementById("marketingVal");
    const demandValDisp = document.getElementById("demandVal");
    const projRevDisp = document.getElementById("simProjRevenue");
    const projProfitDisp = document.getElementById("simProjProfit");

    if (!mktgSlider || !demandSlider || !projRevDisp || !projProfitDisp) return;

    const baseRevenue = 8.42; // Base in Millions
    const baseMargin = 0.267; // 26.7% base margin

    const recalculateScenario = () => {
      const mktgPct = parseFloat(mktgSlider.value);
      const demandPct = parseFloat(demandSlider.value);

      // Display updated slider tags
      mktgValDisp.textContent = `${mktgPct >= 0 ? "+" : ""}${mktgPct}%`;
      demandValDisp.textContent = `${demandPct >= 0 ? "+" : ""}${demandPct}%`;

      // Simplified demo elasticity model
      // Revenue gain = (Demand * 0.7) + (Marketing * 0.45)
      const revenueGrowthPct = (demandPct * 0.7) + (mktgPct * 0.45);
      const projectedRev = baseRevenue * (1 + revenueGrowthPct / 100);

      // Profit impact factors marketing acquisition friction
      const profitGrowthPct = (demandPct * 0.55) + (mktgPct * 0.25);

      projRevDisp.textContent = `₹${projectedRev.toFixed(2)}M`;
      projProfitDisp.textContent = `${profitGrowthPct >= 0 ? "+" : ""}${profitGrowthPct.toFixed(1)}%`;
    };

    mktgSlider.addEventListener("input", recalculateScenario);
    demandSlider.addEventListener("input", recalculateScenario);
  };

  /* ==========================================================================
     5. LIGHTWEIGHT HERO BACKGROUND PARTICLES (36 OPTIMIZED NODES)
     ========================================================================== */
  const initCanvasParticles = () => {
    const canvas = document.getElementById("howParticleCanvas");
    if (!canvas || prefersReducedMotion) return;

    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const particleCount = Math.min(Math.floor(window.innerWidth / 38), 36);
    const particles = [];
    const colorPalette = [
      "rgba(117, 103, 248,",
      "rgba(63, 169, 245,",
      "rgba(57, 217, 138,",
    ];

    class NodeParticle {
      constructor() {
        this.reset();
      }

      reset() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = (Math.random() - 0.5) * 0.35;
        this.vy = (Math.random() - 0.5) * 0.35;
        this.radius = Math.random() * 1.6 + 0.8;
        this.baseColor = colorPalette[Math.floor(Math.random() * colorPalette.length)];
        this.alpha = Math.random() * 0.35 + 0.15;
      }

      update() {
        this.x += this.vx;
        this.y += this.vy;

        if (this.x < 0) this.x = width;
        if (this.x > width) this.x = 0;
        if (this.y < 0) this.y = height;
        if (this.y > height) this.y = 0;
      }

      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = `${this.baseColor} ${this.alpha})`;
        ctx.fill();
      }
    }

    for (let i = 0; i < particleCount; i++) {
      particles.push(new NodeParticle());
    }

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Connect proximal points
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 110) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            const lineAlpha = (1 - dist / 110) * 0.1;
            ctx.strokeStyle = `rgba(63, 169, 245, ${lineAlpha})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }

      particles.forEach((p) => {
        p.update();
        p.draw();
      });

      requestAnimationFrame(render);
    };

    render();

    window.addEventListener("resize", () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });
  };

  /* ==========================================================================
     6. SMOOTH SCROLL FOR "EXPLORE THE JOURNEY" CTA
     ========================================================================== */
  const initSmoothScroll = () => {
    const scrollBtn = document.getElementById("exploreJourneyBtn");
    if (!scrollBtn) return;

    scrollBtn.addEventListener("click", (e) => {
      e.preventDefault();
      const targetSec = document.getElementById("workflowSection");
      if (targetSec) {
        targetSec.scrollIntoView({ behavior: "smooth" });
      }
    });
  };

  // Initialize all modular behaviors
  initScrollReveal();
  initTimelineObserver();
  initHeroPipelineCycler();
  initWhatIfSimulator();
  initCanvasParticles();
  initSmoothScroll();
});