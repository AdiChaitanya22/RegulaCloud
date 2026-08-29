// Configuration
const totalFrames = 300;
const frameIndexFunc = index => `./frames/frame_${index.toString().padStart(4, '0')}.png`;

// DOM Elements
const canvas = document.getElementById('animation-canvas');
const ctx = canvas.getContext('2d');
const loader = document.getElementById('loader');
const progressBar = document.getElementById('progress-bar');
const progressPercent = document.getElementById('progress-percent');
const loaderStatus = document.getElementById('loader-status');
const loadedCountEl = document.getElementById('loaded-count');
const totalCountEl = document.getElementById('total-count');

// State Variables
const images = [];
let loadedCount = 0;
let currentFrame = 0;
let targetFrame = 0;
let isLoaded = false;

// Circular SVG Progress Configuration
const circleRadius = 70;
const circumference = 2 * Math.PI * circleRadius; // ~439.82

// Lock scroll during loading
document.body.classList.add('loading');
totalCountEl.textContent = totalFrames;

// Set up SVG Progress Ring
progressBar.style.strokeDasharray = `${circumference}`;
progressBar.style.strokeDashoffset = `${circumference}`;

// Loader Subtitles depending on progress
function getStatusMessage(percent) {
  if (percent < 20) return "Initializing sequence matrix...";
  if (percent < 45) return "Extracting frame vectors...";
  if (percent < 70) return "Caching buffer allocations...";
  if (percent < 95) return "Calibrating inertial scroll sensors...";
  return "Synchronization complete!";
}

// Update Loader UI
function updateLoader(count) {
  const percent = Math.floor((count / totalFrames) * 100);
  
  // Update numbers
  progressPercent.textContent = `${percent}%`;
  loadedCountEl.textContent = count;
  loaderStatus.textContent = getStatusMessage(percent);

  // Update SVG ring
  const strokeOffset = circumference - (percent / 100) * circumference;
  progressBar.style.strokeDashoffset = strokeOffset;
}

// Preload Frames
function preloadImages() {
  for (let i = 1; i <= totalFrames; i++) {
    const img = new Image();
    
    img.onload = () => {
      loadedCount++;
      updateLoader(loadedCount);
      if (loadedCount === totalFrames) {
        handleAllLoaded();
      }
    };
    
    img.onerror = () => {
      console.warn(`Frame ${i} could not be loaded. Substituting...`);
      loadedCount++;
      updateLoader(loadedCount);
      if (loadedCount === totalFrames) {
        handleAllLoaded();
      }
    };

    img.src = frameIndexFunc(i);
    images.push(img);
  }
}

// Draw Image covering viewport (analogous to background-size: cover) with 1.4x Zoom
function drawImageCover(img) {
  if (!img || !img.complete || img.naturalWidth === 0) return;

  const w = window.innerWidth;
  const h = window.innerHeight;

  const imgWidth = img.naturalWidth;
  const imgHeight = img.naturalHeight;

  const imgRatio = imgWidth / imgHeight;
  const screenRatio = w / h;

  let drawWidth, drawHeight, x, y;
  const zoomFactor = 1.4; // Zoom in the holographic interface

  if (screenRatio > imgRatio) {
    // Screen is wider than image aspect ratio
    drawWidth = w * zoomFactor;
    drawHeight = (w / imgRatio) * zoomFactor;
  } else {
    // Screen is taller than image aspect ratio
    drawHeight = h * zoomFactor;
    drawWidth = (h * imgRatio) * zoomFactor;
  }

  // Center the zoomed image
  x = (w - drawWidth) / 2;
  y = (h - drawHeight) / 2;

  // Clear before drawing
  ctx.clearRect(0, 0, w, h);
  ctx.drawImage(img, x, y, drawWidth, drawHeight);
}

// Scale canvas resolution to support Retina/high-DPI screens
function resizeCanvas() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  const dpr = window.devicePixelRatio || 1;

  canvas.width = w * dpr;
  canvas.height = h * dpr;

  ctx.scale(dpr, dpr);

  // Redraw current frame immediately on resize
  if (isLoaded) {
    const frameIndex = Math.min(totalFrames - 1, Math.max(0, Math.round(currentFrame)));
    drawImageCover(images[frameIndex]);
  }
}

// Setup Event Listeners
window.addEventListener('resize', resizeCanvas);

window.addEventListener('scroll', () => {
  if (!isLoaded) return;
  const scrollTop = window.scrollY;
  const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
  const scrollPercent = maxScroll <= 0 ? 0 : scrollTop / maxScroll;
  
  // Set target frame mapping [0, 299]
  targetFrame = scrollPercent * (totalFrames - 1);
});

// Linear Interpolation (Lerp) Frame Loop for Inertia Easing
function updateAnimation() {
  const ease = 0.08; // Control scroll easing weight (lower = smoother/slower catch up)
  const diff = targetFrame - currentFrame;

  // Update current frame with interpolation
  if (Math.abs(diff) > 0.001) {
    currentFrame += diff * ease;
  } else {
    currentFrame = targetFrame;
  }

  // Determine rounded frame index to render
  const frameIndex = Math.min(totalFrames - 1, Math.max(0, Math.round(currentFrame)));
  const activeImg = images[frameIndex];

  if (activeImg) {
    drawImageCover(activeImg);
  }

  requestAnimationFrame(updateAnimation);
}

// Start visual engine when loaded
function handleAllLoaded() {
  isLoaded = true;
  
  // Setup sizing
  resizeCanvas();

  // Draw initial frame
  drawImageCover(images[0]);

  // Fade out loader
  loader.classList.add('loaded');
  document.body.classList.remove('loading');

  // Launch interpolator loop
  requestAnimationFrame(updateAnimation);
}

// Initialize Application
preloadImages();
