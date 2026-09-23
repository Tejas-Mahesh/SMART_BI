/**
 * ============================================================
 * SMART BI — CONTACT INTERACTIVE SCRIPT
 * ============================================================
 *
 * File:
 * static/js/contact.js
 *
 * Handles:
 * - Scroll reveal
 * - Contact form validation
 * - Completeness progress meter
 * - Django backend submission
 * - CSRF protection
 * - Loading state
 * - Success state
 * - Error handling
 * - Form reset
 * - Canvas particles
 * - Smooth scrolling
 *
 * ============================================================
 */

document.addEventListener("DOMContentLoaded", () => {
    "use strict";

    const rootEl = document.getElementById("smartContactRoot");

    if (!rootEl) {
        return;
    }

    const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;


    /* ============================================================
       1. SCROLL REVEAL OBSERVER
       ============================================================ */

    const initScrollReveal = () => {

        const reveals = rootEl.querySelectorAll(".cnt-reveal");

        if (!reveals.length) {
            return;
        }

        if (prefersReducedMotion) {

            reveals.forEach((el) => {
                el.classList.add("revealed");
            });

            return;
        }

        const observer = new IntersectionObserver(
            (entries, obs) => {

                entries.forEach((entry) => {

                    if (entry.isIntersecting) {

                        entry.target.classList.add("revealed");

                        obs.unobserve(entry.target);
                    }
                });
            },
            {
                root: null,
                threshold: 0.12,
                rootMargin: "0px 0px -50px 0px",
            }
        );

        reveals.forEach((el) => {
            observer.observe(el);
        });
    };


    /* ============================================================
       2. CONTACT FORM
       ============================================================ */

    const initContactForm = () => {

        const form = document.getElementById("smartContactForm");

        const successPanel =
            document.getElementById("contactSuccessPanel");

        const resetBtn =
            document.getElementById("resetFormBtn");

        const submitBtn =
            document.getElementById("contactSubmitBtn");

        const completenessBar =
            document.getElementById("completenessBar");

        const completenessPct =
            document.getElementById("completenessPct");


        if (!form) {
            return;
        }


        /* ========================================================
           FIELD DEFINITIONS
           ======================================================== */

        const fields = {

            name: {

                input: document.getElementById("contactName"),

                group: document.getElementById("groupName"),

                error: document.getElementById("errName"),

                validate: (val) => {

                    if (val.trim().length >= 2) {
                        return null;
                    }

                    return "Please enter your name (minimum 2 characters).";
                }
            },


            email: {

                input: document.getElementById("contactEmail"),

                group: document.getElementById("groupEmail"),

                error: document.getElementById("errEmail"),

                validate: (val) => {

                    const value = val.trim();

                    if (!value) {

                        return "Please enter your email address.";
                    }

                    const emailPattern =
                        /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

                    if (!emailPattern.test(value)) {

                        return "Please enter a valid email address.";
                    }

                    return null;
                }
            },


            subject: {

                input: document.getElementById("contactSubject"),

                group: document.getElementById("groupSubject"),

                error: document.getElementById("errSubject"),

                validate: (val) => {

                    if (val.trim().length >= 3) {

                        return null;
                    }

                    return "Please enter a subject (minimum 3 characters).";
                }
            },


            message: {

                input: document.getElementById("contactMessage"),

                group: document.getElementById("groupMessage"),

                error: document.getElementById("errMessage"),

                validate: (val) => {

                    if (val.trim().length >= 10) {

                        return null;
                    }

                    return "Please enter a message (minimum 10 characters).";
                }
            }
        };


        /* ========================================================
           COMPLETENESS METER
           ======================================================== */

        const updateCompleteness = () => {

            let validCount = 0;

            const totalFields =
                Object.keys(fields).length;


            Object.values(fields).forEach((field) => {

                if (!field.input) {
                    return;
                }

                if (!field.validate(field.input.value)) {

                    validCount++;
                }
            });


            const pct = Math.round(
                (validCount / totalFields) * 100
            );


            if (completenessBar) {

                completenessBar.style.width =
                    `${pct}%`;
            }


            if (completenessPct) {

                completenessPct.textContent =
                    `${pct}%`;
            }
        };


        /* ========================================================
           FIELD VALIDATION
           ======================================================== */

        const validateField = (
            fieldKey,
            showErrorMessage = true
        ) => {

            const field = fields[fieldKey];

            if (!field || !field.input) {
                return false;
            }


            const errorMessage =
                field.validate(
                    field.input.value
                );


            if (errorMessage) {

                if (showErrorMessage) {

                    field.group.classList.add(
                        "has-error"
                    );

                    field.group.classList.remove(
                        "is-valid"
                    );

                    field.error.textContent =
                        errorMessage;
                }

                return false;
            }


            field.group.classList.remove(
                "has-error"
            );

            field.group.classList.add(
                "is-valid"
            );

            field.error.textContent = "";

            return true;
        };


        /* ========================================================
           INPUT EVENT LISTENERS
           ======================================================== */

        Object.keys(fields).forEach((key) => {

            const field = fields[key];

            if (!field.input) {
                return;
            }


            field.input.addEventListener(
                "focus",
                () => {

                    field.group.classList.add(
                        "focused"
                    );
                }
            );


            field.input.addEventListener(
                "blur",
                () => {

                    field.group.classList.remove(
                        "focused"
                    );

                    validateField(
                        key,
                        true
                    );

                    updateCompleteness();
                }
            );


            field.input.addEventListener(
                "input",
                () => {

                    if (
                        field.group.classList.contains(
                            "has-error"
                        )
                    ) {

                        validateField(
                            key,
                            true
                        );
                    }

                    updateCompleteness();
                }
            );
        });


        /* ========================================================
           GET CSRF TOKEN
           ======================================================== */

        const getCSRFToken = () => {

            const csrfInput =
                form.querySelector(
                    'input[name="csrfmiddlewaretoken"]'
                );

            if (csrfInput) {
                return csrfInput.value;
            }


            const csrfCookie =
                document.cookie
                    .split("; ")
                    .find(
                        (row) =>
                            row.startsWith(
                                "csrftoken="
                            )
                    );


            if (csrfCookie) {

                return decodeURIComponent(
                    csrfCookie.split("=")[1]
                );
            }


            return "";
        };


        /* ========================================================
           SHOW FORM ERROR
           ======================================================== */

        const showFormError = (message) => {

            let errorBox =
                document.getElementById(
                    "contactBackendError"
                );


            if (!errorBox) {

                errorBox =
                    document.createElement("div");

                errorBox.id =
                    "contactBackendError";

                errorBox.className =
                    "cnt-backend-error";

                errorBox.setAttribute(
                    "role",
                    "alert"
                );


                form.insertBefore(
                    errorBox,
                    form.firstChild
                );
            }


            errorBox.textContent = message;

            errorBox.style.display = "block";


            errorBox.scrollIntoView({
                behavior: prefersReducedMotion
                    ? "auto"
                    : "smooth",
                block: "nearest"
            });
        };


        /* ========================================================
           HIDE FORM ERROR
           ======================================================== */

        const hideFormError = () => {

            const errorBox =
                document.getElementById(
                    "contactBackendError"
                );


            if (errorBox) {

                errorBox.style.display =
                    "none";

                errorBox.textContent = "";
            }
        };


        /* ========================================================
           RESET SUBMIT BUTTON
           ======================================================== */

        const resetSubmitButton = () => {

            if (!submitBtn) {
                return;
            }


            submitBtn.disabled = false;

            submitBtn.classList.remove(
                "is-loading"
            );


            const spinner =
                submitBtn.querySelector(
                    ".cnt-btn-spinner"
                );

            const btnText =
                submitBtn.querySelector(
                    ".cnt-btn-text"
                );

            const btnIcon =
                submitBtn.querySelector(
                    ".cnt-btn-icon"
                );


            if (spinner) {

                spinner.style.display =
                    "none";
            }


            if (btnText) {

                btnText.textContent =
                    "Send Message";
            }


            if (btnIcon) {

                btnIcon.style.display =
                    "inline-block";
            }
        };


        /* ========================================================
           SHOW LOADING STATE
           ======================================================== */

        const showLoadingState = () => {

            if (!submitBtn) {
                return;
            }


            submitBtn.disabled = true;

            submitBtn.classList.add(
                "is-loading"
            );


            const spinner =
                submitBtn.querySelector(
                    ".cnt-btn-spinner"
                );

            const btnText =
                submitBtn.querySelector(
                    ".cnt-btn-text"
                );

            const btnIcon =
                submitBtn.querySelector(
                    ".cnt-btn-icon"
                );


            if (spinner) {

                spinner.style.display =
                    "inline-block";
            }


            if (btnText) {

                btnText.textContent =
                    "Sending Message...";
            }


            if (btnIcon) {

                btnIcon.style.display =
                    "none";
            }
        };


        /* ========================================================
           SHOW SUCCESS PANEL
           ======================================================== */

        const showSuccessState = () => {

            form.style.display = "none";


            if (successPanel) {

                successPanel.style.display =
                    "flex";


                successPanel.scrollIntoView({
                    behavior: prefersReducedMotion
                        ? "auto"
                        : "smooth",
                    block: "nearest"
                });
            }


            resetSubmitButton();
        };


        /* ========================================================
           DJANGO BACKEND FORM SUBMISSION
           ======================================================== */

        form.addEventListener(
            "submit",
            async (event) => {

                event.preventDefault();


                hideFormError();


                /* -----------------------------------------------
                   VALIDATE ALL FIELDS
                   ----------------------------------------------- */

                let isFormValid = true;


                Object.keys(fields).forEach(
                    (key) => {

                        const isValid =
                            validateField(
                                key,
                                true
                            );


                        if (!isValid) {

                            isFormValid =
                                false;
                        }
                    }
                );


                updateCompleteness();


                /* -----------------------------------------------
                   STOP IF INVALID
                   ----------------------------------------------- */

                if (!isFormValid) {

                    const firstErrorField =
                        form.querySelector(
                            ".has-error input, .has-error textarea"
                        );


                    if (firstErrorField) {

                        firstErrorField.focus();
                    }


                    return;
                }


                /* -----------------------------------------------
                   LOADING
                   ----------------------------------------------- */

                showLoadingState();


                try {

                    const csrfToken =
                        getCSRFToken();


                    if (!csrfToken) {

                        throw new Error(
                            "Security token is missing. Please refresh the page and try again."
                        );
                    }


                    /* -------------------------------------------
                       SEND FORM TO CURRENT DJANGO URL
                       ------------------------------------------- */

                    const response =
                        await fetch(
                            form.action ||
                            window.location.href,
                            {
                                method: "POST",

                                body:
                                    new FormData(form),

                                headers: {

                                    "X-CSRFToken":
                                        csrfToken,

                                    "X-Requested-With":
                                        "XMLHttpRequest",

                                    "Accept":
                                        "application/json"
                                },

                                credentials:
                                    "same-origin"
                            }
                        );


                    /* -------------------------------------------
                       READ RESPONSE
                       ------------------------------------------- */

                    let data = null;

                    const contentType =
                        response.headers.get(
                            "content-type"
                        );


                    if (
                        contentType &&
                        contentType.includes(
                            "application/json"
                        )
                    ) {

                        data =
                            await response.json();
                    }


                    /* -------------------------------------------
                       HTTP ERROR
                       ------------------------------------------- */

                    if (!response.ok) {

                        if (
                            data &&
                            data.errors
                        ) {

                            Object.entries(
                                data.errors
                            ).forEach(
                                ([fieldName, error]) => {

                                    const field =
                                        fields[fieldName];

                                    if (
                                        field &&
                                        field.group &&
                                        field.error
                                    ) {

                                        field.group.classList.add(
                                            "has-error"
                                        );

                                        field.group.classList.remove(
                                            "is-valid"
                                        );

                                        field.error.textContent =
                                            Array.isArray(error)
                                                ? error.join(" ")
                                                : error;
                                    }
                                }
                            );
                        }


                        throw new Error(
                            data &&
                            data.message
                                ? data.message
                                : "Unable to send your message. Please try again."
                        );
                    }


                    /* -------------------------------------------
                       DJANGO SUCCESS
                       ------------------------------------------- */

                    if (
                        data &&
                        data.success === false
                    ) {

                        throw new Error(
                            data.message ||
                            "Unable to send your message."
                        );
                    }


                    showSuccessState();


                } catch (error) {

                    console.error(
                        "Smart BI Contact Error:",
                        error
                    );


                    resetSubmitButton();


                    showFormError(
                        error.message ||
                        "Something went wrong while sending your message. Please try again."
                    );
                }
            }
        );


        /* ========================================================
           RESET FORM
           ======================================================== */

        if (resetBtn) {

            resetBtn.addEventListener(
                "click",
                () => {

                    form.reset();


                    Object.values(fields).forEach(
                        (field) => {

                            if (!field.group) {
                                return;
                            }


                            field.group.classList.remove(
                                "has-error",
                                "is-valid",
                                "focused"
                            );


                            if (field.error) {

                                field.error.textContent =
                                    "";
                            }
                        }
                    );


                    hideFormError();


                    updateCompleteness();


                    if (successPanel) {

                        successPanel.style.display =
                            "none";
                    }


                    form.style.display =
                        "flex";


                    resetSubmitButton();


                    if (
                        fields.name &&
                        fields.name.input
                    ) {

                        fields.name.input.focus();
                    }
                }
            );
        }


        /* ========================================================
           INITIAL COMPLETENESS
           ======================================================== */

        updateCompleteness();
    };


    /* ============================================================
       3. LIGHTWEIGHT CANVAS PARTICLES
       ============================================================ */

    const initCanvasParticles = () => {

        const canvas =
            document.getElementById(
                "cntParticleCanvas"
            );


        if (
            !canvas ||
            prefersReducedMotion
        ) {

            return;
        }


        const ctx =
            canvas.getContext("2d");


        if (!ctx) {
            return;
        }


        let width =
            (canvas.width =
                window.innerWidth);


        let height =
            (canvas.height =
                window.innerHeight);


        const particleCount =
            Math.min(
                Math.floor(
                    window.innerWidth / 40
                ),
                32
            );


        const particles = [];


        const colorPalette = [

            "rgba(117, 103, 248,",

            "rgba(63, 169, 245,",

            "rgba(57, 217, 138,"
        ];


        class NodeParticle {

            constructor() {

                this.reset();
            }


            reset() {

                this.x =
                    Math.random() * width;

                this.y =
                    Math.random() * height;

                this.vx =
                    (Math.random() - 0.5) *
                    0.35;

                this.vy =
                    (Math.random() - 0.5) *
                    0.35;

                this.radius =
                    Math.random() * 1.5 +
                    0.8;

                this.baseColor =
                    colorPalette[
                        Math.floor(
                            Math.random() *
                            colorPalette.length
                        )
                    ];

                this.alpha =
                    Math.random() * 0.35 +
                    0.15;
            }


            update() {

                this.x += this.vx;

                this.y += this.vy;


                if (this.x < 0) {
                    this.x = width;
                }

                if (this.x > width) {
                    this.x = 0;
                }

                if (this.y < 0) {
                    this.y = height;
                }

                if (this.y > height) {
                    this.y = 0;
                }
            }


            draw() {

                ctx.beginPath();

                ctx.arc(
                    this.x,
                    this.y,
                    this.radius,
                    0,
                    Math.PI * 2
                );

                ctx.fillStyle =
                    `${this.baseColor} ${this.alpha})`;

                ctx.fill();
            }
        }


        for (
            let i = 0;
            i < particleCount;
            i++
        ) {

            particles.push(
                new NodeParticle()
            );
        }


        const render = () => {

            ctx.clearRect(
                0,
                0,
                width,
                height
            );


            /* -----------------------------------------------
               CONNECT NEARBY PARTICLES
               ----------------------------------------------- */

            for (
                let i = 0;
                i < particles.length;
                i++
            ) {

                for (
                    let j = i + 1;
                    j < particles.length;
                    j++
                ) {

                    const dx =
                        particles[i].x -
                        particles[j].x;

                    const dy =
                        particles[i].y -
                        particles[j].y;

                    const distance =
                        Math.sqrt(
                            dx * dx +
                            dy * dy
                        );


                    if (distance < 110) {

                        ctx.beginPath();

                        ctx.moveTo(
                            particles[i].x,
                            particles[i].y
                        );

                        ctx.lineTo(
                            particles[j].x,
                            particles[j].y
                        );


                        const lineAlpha =
                            (1 - distance / 110) *
                            0.1;


                        ctx.strokeStyle =
                            `rgba(63, 169, 245, ${lineAlpha})`;

                        ctx.lineWidth =
                            0.8;

                        ctx.stroke();
                    }
                }
            }


            particles.forEach(
                (particle) => {

                    particle.update();

                    particle.draw();
                }
            );


            requestAnimationFrame(
                render
            );
        };


        render();


        window.addEventListener(
            "resize",
            () => {

                width =
                    canvas.width =
                    window.innerWidth;

                height =
                    canvas.height =
                    window.innerHeight;
            }
        );
    };


    /* ============================================================
       4. SMOOTH SCROLL
       ============================================================ */

    const initSmoothScroll = () => {

        const startBtn =
            document.getElementById(
                "startConvoBtn"
            );


        if (!startBtn) {
            return;
        }


        startBtn.addEventListener(
            "click",
            (event) => {

                event.preventDefault();


                const targetSection =
                    document.getElementById(
                        "mainContactSection"
                    );


                if (targetSection) {

                    targetSection.scrollIntoView({
                        behavior:
                            prefersReducedMotion
                                ? "auto"
                                : "smooth"
                    });
                }
            }
        );
    };


    /* ============================================================
       5. INITIALIZE EVERYTHING
       ============================================================ */

    initScrollReveal();

    initContactForm();

    initCanvasParticles();

    initSmoothScroll();

});