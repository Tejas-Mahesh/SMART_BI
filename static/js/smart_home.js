/**
 * SMART BI — CINEMATIC DECISION INTELLIGENCE SYSTEM
 * File: static/js/smart_home.js
 * Vanilla JavaScript implementation for interactive visual behaviors,
 * 3D tilt, canvas particles, counters, timeline observation, and SVG paths.
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
     2. 3D HERO PERSPECTIVE TILT & FLOATING PARALLAX
     ========================================================================== */
  const initHeroTiltAndParallax = () => {
    if (prefersReducedMotion) return;

    const heroSection = document.getElementById("heroSection");
    const tiltCard = document.getElementById("dashboardTiltCard");
    const floatingCards = document.querySelectorAll(".floating-card");

    if (!heroSection || !tiltCard) return;

    let targetRotX = 4;
    let targetRotY = -6;
    let currentRotX = 4;
    let currentRotY = -6;

    let mouseX = 0;
    let mouseY = 0;
    let isHoveringHero = false;
    let animationFrameId = null;

    const updateOrientation = () => {
      currentRotX += (targetRotX - currentRotX) * 0.08;
      currentRotY += (targetRotY - currentRotY) * 0.08;

      tiltCard.style.transform = `rotateX(${currentRotX.toFixed(2)}deg) rotateY(${currentRotY.toFixed(2)}deg) translateZ(0)`;

      floatingCards.forEach((card) => {
        const speed = parseFloat(card.getAttribute("data-speed")) || 1.0;
        const offsetX = (mouseX * speed * 15).toFixed(2);
        const offsetY = (mouseY * speed * 15).toFixed(2);
        card.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
      });

      if (isHoveringHero || Math.abs(targetRotX - currentRotX) > 0.01 || Math.abs(targetRotY - currentRotY) > 0.01) {
        animationFrameId = requestAnimationFrame(updateOrientation);
      } else {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
      }
    };

    heroSection.addEventListener("mouseenter", () => {
      isHoveringHero = true;
      if (!animationFrameId) {
        animationFrameId = requestAnimationFrame(updateOrientation);
      }
    });

    heroSection.addEventListener("mousemove", (event) => {
      const rect = heroSection.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      mouseX = (x / rect.width - 0.5) * 2;
      mouseY = (y / rect.height - 0.5) * 2;

      // Restrict rotation bounds to subtle degree windows
      targetRotY = -6 + mouseX * 7;
      targetRotX = 4 - mouseY * 7;

      if (!animationFrameId) {
        animationFrameId = requestAnimationFrame(updateOrientation);
      }
    });

    heroSection.addEventListener("mouseleave", () => {
      isHoveringHero = false;
      mouseX = 0;
      mouseY = 0;
      targetRotX = 4;
      targetRotY = -6;
    });
  };

  /* ==========================================================================
     3. KPI METRIC COUNTER ANIMATIONS
     ========================================================================== */
  const initKpiCounters = () => {
    const counters = document.querySelectorAll(".kpi-counter");
    if (!counters.length) return;

    const counterObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const target = parseFloat(el.getAttribute("data-target")) || 0;
          const decimals = parseInt(el.getAttribute("data-decimals"), 10) || 0;
          const duration = 1800;
          const startTime = performance.now();

          const updateCounter = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const currentVal = (target * easeOut).toFixed(decimals);

            el.textContent = currentVal;

            if (progress < 1) {
              requestAnimationFrame(updateCounter);
            } else {
              el.textContent = target.toFixed(decimals);
            }
          };

          requestAnimationFrame(updateCounter);
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.25 });

    counters.forEach((c) => counterObserver.observe(c));
  };

  /* ==========================================================================
     4. HERO CANVAS PARTICLES (OPTIMIZED 45 NODES)
     ========================================================================== */
  const initHeroParticles = () => {
    const canvas = document.getElementById("heroParticleCanvas");
    if (!canvas || prefersReducedMotion) return;

    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const particleCount = Math.min(Math.floor(window.innerWidth / 35), 45);
    const particles = [];
    const colors = ["rgba(53, 184, 255,", "rgba(124, 92, 255,", "rgba(34, 211, 238,"];

    class Particle {
      constructor() {
        this.reset();
      }

      reset() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = (Math.random() - 0.5) * 0.45;
        this.vy = (Math.random() - 0.5) * 0.45;
        this.radius = Math.random() * 1.8 + 0.8;
        this.baseColor = colors[Math.floor(Math.random() * colors.length)];
        this.alpha = Math.random() * 0.45 + 0.15;
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

          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            const lineAlpha = (1 - dist / 120) * 0.12;
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
     5. FORECAST CHART PATH DRAW-IN ANIMATION
     ========================================================================== */
  const initForecastDraw = () => {
    const forecastGraph = document.getElementById("forecastGraph");
    const histPath = document.getElementById("histLinePath");
    const forecastPath = document.getElementById("forecastLinePath");
    const endpoint = document.getElementById("predictionEndpoint");
    const pin = document.getElementById("predictionPin");

    if (!forecastGraph || !histPath || !forecastPath) return;

    if (prefersReducedMotion) {
      if (endpoint) endpoint.style.opacity = "1";
      if (pin) pin.style.opacity = "1";
      return;
    }

    const histLength = histPath.getTotalLength();
    const forecastLength = forecastPath.getTotalLength();

    histPath.style.strokeDasharray = histLength;
    histPath.style.strokeDashoffset = histLength;
    histPath.style.transition = "stroke-dashoffset 1.4s cubic-bezier(0.16, 1, 0.3, 1)";

    forecastPath.style.strokeDasharray = forecastLength;
    forecastPath.style.strokeDashoffset = forecastLength;
    forecastPath.style.transition = "stroke-dashoffset 1.2s cubic-bezier(0.16, 1, 0.3, 1)";

    if (endpoint) {
      endpoint.style.opacity = "0";
      endpoint.style.transition = "opacity 0.5s ease 2.2s";
    }

    if (pin) {
      pin.style.opacity = "0";
      pin.style.transform = "translateY(10px)";
      pin.style.transition = "opacity 0.6s ease 2.4s, transform 0.6s ease 2.4s";
    }

    const graphObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          // Draw historical first
          histPath.style.strokeDashoffset = "0";

          // Then draw forecast corridor
          setTimeout(() => {
            forecastPath.style.strokeDashoffset = "0";
          }, 1100);

          // Reveal endpoint & confidence pin
          if (endpoint) endpoint.style.opacity = "1";
          if (pin) {
            pin.style.opacity = "1";
            pin.style.transform = "translateY(0)";
          }

          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.35 });

    graphObserver.observe(forecastGraph);
  };

  /* ==========================================================================
     6. BUSINESS QUESTIONS ACTIVE STEP SCROLL OBSERVER
     ========================================================================== */
  const initTimelineObserver = () => {
    const timelineRows = document.querySelectorAll(".timeline-row");
    if (!timelineRows.length) return;

    const timelineObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          timelineRows.forEach((row) => row.classList.remove("active"));
          entry.target.classList.add("active");
        }
      });
    }, {
      root: null,
      threshold: 0.6,
      rootMargin: "0px 0px -20% 0px",
    });

    timelineRows.forEach((row) => timelineObserver.observe(row));
  };

  /* ==========================================================================
     7. DATA NETWORK NODE HOVER SIGNAL BEAMS
     ========================================================================== */
  const initNetworkInteractions = () => {
    const nodes = document.querySelectorAll(".data-node");
    const beams = document.querySelectorAll(".net-wire-beam");

    if (!nodes.length || !beams.length) return;

    nodes.forEach((node, index) => {
      node.addEventListener("mouseenter", () => {
        beams.forEach((b) => (b.style.opacity = "0.2"));
        if (beams[index]) {
          beams[index].style.opacity = "1";
          beams[index].style.strokeWidth = "4px";
          beams[index].style.filter = "drop-shadow(0 0 10px #22D3EE)";
        }
      });

      node.addEventListener("mouseleave", () => {
        beams.forEach((b) => {
          b.style.opacity = "1";
          b.style.strokeWidth = "2.5px";
          b.style.filter = "none";
        });
      });
    });
  };

  // Initialize all interactive modules
  initScrollReveal();
  initHeroTiltAndParallax();
  initKpiCounters();
  initHeroParticles();
  initForecastDraw();
  initTimelineObserver();
  initNetworkInteractions();
});