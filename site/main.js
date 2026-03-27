/**
 * 叫魂 Soulstealer — Multi-page Site Script
 */

(function () {
  'use strict';

  // ===== Navbar scroll effect =====
  const navbar = document.getElementById('navbar');

  window.addEventListener('scroll', function () {
    if (window.scrollY > 60) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });

  // ===== Mobile nav toggle =====
  var toggle = document.querySelector('.nav-toggle');
  var navLinks = document.querySelector('.nav-links');

  if (toggle) {
    toggle.addEventListener('click', function () {
      navLinks.classList.toggle('open');
    });

    navLinks.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        navLinks.classList.remove('open');
      });
    });
  }

  // ===== Scroll reveal =====
  var revealElements = document.querySelectorAll('.reveal');

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    },
    { threshold: 0.1 }
  );

  revealElements.forEach(function (el) { observer.observe(el); });

  // ===== Ink background canvas =====
  var canvas = document.getElementById('ink-bg');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  resize();
  window.addEventListener('resize', resize);

  var particles = [];
  var PARTICLE_COUNT = 35;

  function Particle() {
    this.reset();
  }

  Particle.prototype.reset = function () {
    this.x = Math.random() * canvas.width;
    this.y = Math.random() * canvas.height;
    this.size = Math.random() * 80 + 20;
    this.speedX = (Math.random() - 0.5) * 0.15;
    this.speedY = (Math.random() - 0.5) * 0.1;
    this.opacity = Math.random() * 0.04 + 0.01;
    this.life = Math.random() * 1000 + 500;
    this.age = 0;
  };

  Particle.prototype.update = function () {
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
  };

  Particle.prototype.draw = function () {
    var fade = 1 - this.age / this.life;
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(178, 34, 34, ' + (this.opacity * fade) + ')';
    ctx.fill();
  };

  for (var i = 0; i < PARTICLE_COUNT; i++) {
    var p = new Particle();
    p.age = Math.floor(Math.random() * p.life);
    particles.push(p);
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (var i = 0; i < particles.length; i++) {
      particles[i].update();
      particles[i].draw();
    }
    requestAnimationFrame(animate);
  }

  var prefersReducedMotion = window.matchMedia(
    '(prefers-reduced-motion: reduce)'
  ).matches;

  if (!prefersReducedMotion) {
    animate();
  }

  // ===== Smooth scroll for anchor links =====
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
})();
