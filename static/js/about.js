/**
 * SMART BI — ABOUT PAGE INTERACTIVE INTELLIGENCE ENGINE
 * File: static/js/about.js
 * Vanilla JavaScript implementation for scroll-reveal observers,
 * interactive intelligence core, mouse parallax, domain constellation nodes,
 * connected layers timeline, dynamic particle canvas, and pipeline loops.
 */

document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ==========================================================================
     1. SCROLL REVEAL OBSERVER
     ========================================================================== */
  const initScrollReveal = () => {
    const revealElements = document.querySelectorAll(".reveal-fade");
    if (!revealElements.length) return;

    if (prefersReducedMotion) {
      revealElements.forEach((el) => el.classList.add("revealed"));
      return;
    }

    const observerOptions = {
      root: null,
      rootMargin: "0px 0px -60px 0px",
      threshold: 0.12,
    };

    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          observer.unobserve(entry.target);
        }
      });
    }, observerOptions);

    revealElements.forEach((el) => revealObserver.observe(el));
  };

  /* ==========================================================================
     2. ABOUT HERO CORE MOUSE PARALLAX
     ========================================================================== */
  const initHeroParallax = () => {
    if (prefersReducedMotion) return;

    const heroSection = document.getElementById("aboutHero");
    const coreAssembly = document.getElementById("coreAssembly");
    const satellites = document.querySelectorAll(".floating-satellite");

    if (!heroSection || !coreAssembly) return;

    let mouseX = 0;
    let mouseY = 0;
    let currentX = 0;
    let currentY = 0;
    let isHovering = false;
    let animFrame = null;

    const updateParallax = () => {
      currentX += (mouseX - currentX) * 0.06;
      currentY += (mouseY - currentY) * 0.06;

      coreAssembly.style.transform = `translate3d(${currentX * 16}px, ${currentY * 16}px, 0)`;

      satellites.forEach((sat, idx) => {
        const factor = (idx % 2 === 0 ? 1 : -1) * (0.8 + (idx * 0.15));
        sat.style.transform = `translate3d(${-currentX * factor * 14}px, ${-currentY * factor * 14}px, 0)`;
      });

      if (isHovering || Math.abs(mouseX - currentX) > 0.001 || Math.abs(mouseY - currentY) > 0.001) {
        animFrame = requestAnimationFrame(updateParallax);
      } else {
        cancelAnimationFrame(animFrame);
        animFrame = null;
      }
    };

    heroSection.addEventListener("mouseenter", () => {
      isHovering = true;
      if (!animFrame) animFrame = requestAnimationFrame(updateParallax);
    });

    heroSection.addEventListener("mousemove", (e) => {
      const rect = heroSection.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      mouseX = (x / rect.width - 0.5) * 2;
      mouseY = (y / rect.height - 0.5) * 2;

      if (!animFrame) animFrame = requestAnimationFrame(updateParallax);
    });

    heroSection.addEventListener("mouseleave", () => {
      isHovering = false;
      mouseX = 0;
      mouseY = 0;
    });
  };

  /* ==========================================================================
     3. LIGHTWEIGHT ABOUT PARTICLES CANVAS (35 OPTIMIZED NODES)
     ========================================================================== */
  const initAboutParticles = () => {
    const canvas = document.getElementById("aboutParticleCanvas");
    if (!canvas || prefersReducedMotion) return;

    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const particleCount = Math.min(Math.floor(window.innerWidth / 40), 38);
    const particles = [];
    const colors = [
      "rgba(124, 92, 255,",
      "rgba(53, 184, 255,",
      "rgba(34, 211, 238,",
      "rgba(57, 229, 140,",
    ];

    class Particle {
      constructor() {
        this.reset();
      }

      reset() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = (Math.random() - 0.5) * 0.4;
        this.vy = (Math.random() - 0.5) * 0.4;
        this.radius = Math.random() * 1.7 + 0.7;
        this.baseColor = colors[Math.floor(Math.random() * colors.length)];
        this.alpha = Math.random() * 0.4 + 0.15;
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
      particles.push(new Particle());
    }

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Connect proximal nodes
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 110) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            const lineAlpha = (1 - dist / 110) * 0.11;
            ctx.strokeStyle = `rgba(53, 184, 255, ${lineAlpha})`;
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
     4. CONNECTED INTELLIGENCE LAYERS: SCROLL-DRIVEN ACTIVE RUNNER
     ========================================================================== */
  const initLayersTimeline = () => {
    const layerItems = document.querySelectorAll(".layer-item");
    const spineRunner = document.getElementById("spineRunner");
    if (!layerItems.length) return;

    const layerObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          layerItems.forEach((item) => item.classList.remove("active"));
          entry.target.classList.add("active");

          if (spineRunner) {
            const index = parseInt(entry.target.getAttribute("data-layer"), 10) - 1;
            // Offset the glow runner along the spine
            const itemOffsetTop = entry.target.offsetTop;
            spineRunner.style.top = `${itemOffsetTop + 15}px`;
          }
        }
      });
    }, {
      root: null,
      threshold: 0.5,
      rootMargin: "0px 0px -20% 0px",
    });

    layerItems.forEach((item) => layerObserver.observe(item));
  };

  /* ==========================================================================
     5. BUSINESS INTELLIGENCE DOMAINS CONSTELLATION HOVER
     ========================================================================== */
  const initDomainsConstellation = () => {
    const domainNodes = document.querySelectorAll(".domain-node");
    const domainWires = document.querySelectorAll(".domain-wire");

    if (!domainNodes.length) return;

    domainNodes.forEach((node) => {
      const targetDomain = node.getAttribute("data-target");
      const matchedWire = document.querySelector(`.wire-${targetDomain}`);

      const activateNode = () => {
        domainWires.forEach((w) => w.classList.remove("wire-active"));
        if (matchedWire) {
          matchedWire.classList.add("wire-active");
        }
      };

      const deactivateNode = () => {
        if (matchedWire) {
          matchedWire.classList.remove("wire-active");
        }
      };

      node.addEventListener("mouseenter", activateNode);
      node.addEventListener("mouseleave", deactivateNode);
      node.addEventListener("focus", activateNode);
      node.addEventListener("blur", deactivateNode);
    });
  };

  /* ==========================================================================
     6. DATA TO DECISION PIPELINE SYNCHRONIZED BEAT
     ========================================================================== */
  const initPipelineSync = () => {
    const stationCells = document.querySelectorAll(".station-cell");
    if (!stationCells.length || prefersReducedMotion) return;

    let currentStationIndex = 0;
    const totalStations = stationCells.length;

    // Loop through stations sequentially in cadence with the bead transit
    setInterval(() => {
      stationCells.forEach((cell) => cell.classList.remove("active"));
      stationCells[currentStationIndex].classList.add("active");

      currentStationIndex = (currentStationIndex + 1) % totalStations;
    }, 650);
  };

  /* ==========================================================================
     7. BUTTON MAGNETIC / AMBIENT GLOW FEEDBACK
     ========================================================================== */
  const initButtonGlowFeedback = () => {
    if (prefersReducedMotion) return;

    const glowButtons = document.querySelectorAll(".btn-primary-glow");
    glowButtons.forEach((btn) => {
      btn.addEventListener("mousemove", (e) => {
        const rect = btn.getBoundingClientRect();
        const x = e.clientX - rect.left - rect.width / 2;
        const y = e.clientY - rect.top - rect.height / 2;

        btn.style.transform = `translate3d(${x * 0.12}px, ${y * 0.12}px, 0) translateY(-2px)`;
      });

      btn.addEventListener("mouseleave", () => {
        btn.style.transform = "";
      });
    });
  };

  // Initialize all modular behaviors
  initScrollReveal();
  initHeroParallax();
  initAboutParticles();
  initLayersTimeline();
  initDomainsConstellation();
  initPipelineSync();
  initButtonGlowFeedback();
});