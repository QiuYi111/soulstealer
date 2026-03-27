/**
 * 叫魂 Soulstealer — Main Site Script
 */

(function () {
  'use strict';

  // ===== Navbar scroll effect =====
  const navbar = document.getElementById('navbar');
  let lastScroll = 0;

  window.addEventListener('scroll', () => {
    const current = window.scrollY;
    if (current > 60) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
    lastScroll = current;
  });

  // ===== Scroll reveal =====
  const revealElements = document.querySelectorAll(
    '.about-card, .feature-card, .arch-layer, .timeline-item, .cta-box'
  );

  revealElements.forEach((el) => el.classList.add('reveal'));

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    },
    { threshold: 0.15 }
  );

  revealElements.forEach((el) => observer.observe(el));

  // ===== Ink background canvas =====
  const canvas = document.getElementById('ink-bg');
  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  resize();
  window.addEventListener('resize', resize);

  // Floating ink particles
  const particles = [];
  const PARTICLE_COUNT = 40;

  class Particle {
    constructor() {
      this.reset();
    }

    reset() {
      this.x = Math.random() * canvas.width;
      this.y = Math.random() * canvas.height;
      this.size = Math.random() * 80 + 20;
      this.speedX = (Math.random() - 0.5) * 0.15;
      this.speedY = (Math.random() - 0.5) * 0.1;
      this.opacity = Math.random() * 0.04 + 0.01;
      this.life = Math.random() * 1000 + 500;
      this.age = 0;
    }

    update() {
      this.x += this.speedX;
      this.y += this.speedY;
      this.age++;

      if (
        this.age > this.life ||
        this.x < -this.size ||
        this.x > canvas.width + this.size ||
        this.y < -this.size ||
        this.y > canvas.height + this.size
      ) {
        this.reset();
      }
    }

    draw() {
      const fade = 1 - this.age / this.life;
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(178, 34, 34, ${this.opacity * fade})`;
      ctx.fill();
    }
  }

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const p = new Particle();
    p.age = Math.random() * p.life; // stagger
    particles.push(p);
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach((p) => {
      p.update();
      p.draw();
    });
    requestAnimationFrame(animate);
  }

  // Respect prefers-reduced-motion
  const prefersReducedMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)'
  ).matches;

  if (!prefersReducedMotion) {
    animate();
  }

  // ===== Smooth scroll for anchor links =====
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (e) => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
})();
