/**
 * SMART BI — CONTACT INTERACTIVE SCRIPT
 * File: static/js/contact.js
 * Vanilla JavaScript implementation for scroll reveal observer, form validation,
 * completeness progress meter, demo submission loading state, success transition,
 * and lightweight canvas particles.
 */

document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  const rootEl = document.getElementById("smartContactRoot");
  if (!rootEl) return;

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ==========================================================================
     1. SCROLL REVEAL OBSERVER
     ========================================================================== */
  const initScrollReveal = () => {
    const reveals = rootEl.querySelectorAll(".cnt-reveal");
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
     2. FORM VALIDATION & COMPLETENESS TRACKER
     ========================================================================== */
  const initContactForm = () => {
    const form = document.getElementById("smartContactForm");
    const successPanel = document.getElementById("contactSuccessPanel");
    const resetBtn = document.getElementById("resetFormBtn");
    const submitBtn = document.getElementById("contactSubmitBtn");
    const completenessBar = document.getElementById("completenessBar");
    const completenessPct = document.getElementById("completenessPct");

    if (!form) return;

    const fields = {
      name: {
        input: document.getElementById("contactName"),
        group: document.getElementById("groupName"),
        error: document.getElementById("errName"),
        validate: (val) => (val.trim().length >= 2 ? null : "Please enter your name (minimum 2 characters).")
      },
      email: {
        input: document.getElementById("contactEmail"),
        group: document.getElementById("groupEmail"),
        error: document.getElementById("errEmail"),
        validate: (val) => {
          const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
          if (!val.trim()) return "Please enter your email address.";
          if (!emailPattern.test(val.trim())) return "Please enter a valid email address.";
          return null;
        }
      },
      subject: {
        input: document.getElementById("contactSubject"),
        group: document.getElementById("groupSubject"),
        error: document.getElementById("errSubject"),
        validate: (val) => (val.trim().length >= 3 ? null : "Please enter a subject (minimum 3 characters).")
      },
      message: {
        input: document.getElementById("contactMessage"),
        group: document.getElementById("groupMessage"),
        error: document.getElementById("errMessage"),
        validate: (val) => (val.trim().length >= 10 ? null : "Please enter a message (minimum 10 characters).")
      }
    };

    // Calculate completeness percentage based on valid inputs
    const updateCompleteness = () => {
      let validCount = 0;
      const totalFields = Object.keys(fields).length;

      Object.values(fields).forEach((f) => {
        if (!f.validate(f.input.value)) {
          validCount++;
        }
      });

      const pct = Math.round((validCount / totalFields) * 100);
      if (completenessBar) completenessBar.style.width = `${pct}%`;
      if (completenessPct) completenessPct.textContent = `${pct}%`;
    };

    // Validate a single field
    const validateField = (fieldKey, showErrorMessage = true) => {
      const f = fields[fieldKey];
      const err = f.validate(f.input.value);

      if (err) {
        if (showErrorMessage) {
          f.group.classList.add("has-error");
          f.group.classList.remove("is-valid");
          f.error.textContent = err;
        }
        return false;
      } else {
        f.group.classList.remove("has-error");
        f.group.classList.add("is-valid");
        f.error.textContent = "";
        return true;
      }
    };

    // Setup input listeners
    Object.keys(fields).forEach((key) => {
      const f = fields[key];

      f.input.addEventListener("focus", () => {
        f.group.classList.add("focused");
      });

      f.input.addEventListener("blur", () => {
        f.group.classList.remove("focused");
        validateField(key, true);
        updateCompleteness();
      });

      f.input.addEventListener("input", () => {
        if (f.group.classList.contains("has-error")) {
          validateField(key, true);
        }
        updateCompleteness();
      });
    });

    // Handle form submission
    form.addEventListener("submit", (e) => {
      e.preventDefault();

      let isFormValid = true;
      Object.keys(fields).forEach((key) => {
        const isValid = validateField(key, true);
        if (!isValid) isFormValid = false;
      });

      updateCompleteness();

      if (!isFormValid) {
        // Focus first field with an error
        const firstErrorField = form.querySelector(".has-error input, .has-error textarea");
        if (firstErrorField) firstErrorField.focus();
        return;
      }

      // ----------------------------------------------------------------------
      // NOTE FOR BACKEND INTEGRATION:
      // Replace the demo submission below with the Django contact endpoint
      // when the backend contact form is implemented.
      // Example:
      // fetch('/api/contact/', { method: 'POST', body: new FormData(form) })
      // ----------------------------------------------------------------------

      // Demonstrate loading state
      submitBtn.disabled = true;
      submitBtn.classList.add("is-loading");
      const spinner = submitBtn.querySelector(".cnt-btn-spinner");
      const btnText = submitBtn.querySelector(".cnt-btn-text");
      const btnIcon = submitBtn.querySelector(".cnt-btn-icon");

      if (spinner) spinner.style.display = "inline-block";
      if (btnText) btnText.textContent = "Preparing Message...";
      if (btnIcon) btnIcon.style.display = "none";

      setTimeout(() => {
        // Show success animation panel
        form.style.display = "none";
        if (successPanel) {
          successPanel.style.display = "flex";
          successPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }

        // Reset submit button state
        submitBtn.disabled = false;
        submitBtn.classList.remove("is-loading");
        if (spinner) spinner.style.display = "none";
        if (btnText) btnText.textContent = "Send Message";
        if (btnIcon) btnIcon.style.display = "inline-block";
      }, 950);
    });

    // Reset button to write another message
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        form.reset();
        Object.values(fields).forEach((f) => {
          f.group.classList.remove("has-error", "is-valid", "focused");
          f.error.textContent = "";
        });
        updateCompleteness();

        if (successPanel) successPanel.style.display = "none";
        form.style.display = "flex";
        fields.name.input.focus();
      });
    }
  };

  /* ==========================================================================
     3. LIGHTWEIGHT CANVAS PARTICLES (32 OPTIMIZED NODES)
     ========================================================================== */
  const initCanvasParticles = () => {
    const canvas = document.getElementById("cntParticleCanvas");
    if (!canvas || prefersReducedMotion) return;

    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const particleCount = Math.min(Math.floor(window.innerWidth / 40), 32);
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
        this.radius = Math.random() * 1.5 + 0.8;
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
     4. SMOOTH SCROLL FOR "START A CONVERSATION"
     ========================================================================== */
  const initSmoothScroll = () => {
    const startBtn = document.getElementById("startConvoBtn");
    if (!startBtn) return;

    startBtn.addEventListener("click", (e) => {
      e.preventDefault();
      const targetSec = document.getElementById("mainContactSection");
      if (targetSec) {
        targetSec.scrollIntoView({ behavior: "smooth" });
      }
    });
  };

  // Initialize all modular controllers
  initScrollReveal();
  initContactForm();
  initCanvasParticles();
  initSmoothScroll();
});