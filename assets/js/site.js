// Taichi Health & Finance Intranet Client JS

(function() {
  // 1. Theme Management
  const savedTheme = localStorage.getItem('taichi_theme') || 
    (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  
  document.documentElement.setAttribute('data-theme', savedTheme);
  
  window.addEventListener('DOMContentLoaded', () => {
    // Add theme toggle button event
    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
      updateToggleText(toggleBtn, savedTheme);
      toggleBtn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('taichi_theme', next);
        updateToggleText(toggleBtn, next);
      });
    }

    // 2. Reading Progress & Back-to-top
    const progressBar = document.getElementById('reading-progress');
    const backToTopBtn = document.getElementById('back-to-top');

    window.addEventListener('scroll', () => {
      const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
      const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      if (progressBar && height > 0) {
        const scrolled = (winScroll / height) * 100;
        progressBar.style.width = scrolled + '%';
      }
      if (backToTopBtn) {
        if (winScroll > 300) {
          backToTopBtn.style.display = 'flex';
        } else {
          backToTopBtn.style.display = 'none';
        }
      }
    });

    if (backToTopBtn) {
      backToTopBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }

    // 3. TOC ScrollSpy
    const tocLinks = document.querySelectorAll('.toc-sidebar a');
    const headings = [];
    tocLinks.forEach(link => {
      const id = link.getAttribute('href')?.replace('#', '');
      if (id) {
        const el = document.getElementById(id);
        if (el) headings.push({ id, el, link });
      }
    });

    if (headings.length > 0) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            tocLinks.forEach(l => l.classList.remove('active'));
            const target = headings.find(h => h.el === entry.target);
            if (target) {
              target.link.classList.add('active');
            }
          }
        });
      }, { rootMargin: '-80px 0px -70% 0px' });

      headings.forEach(h => observer.observe(h.el));
    }

    // 4. Code Block Copy Buttons
    document.querySelectorAll('.copy-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const wrap = btn.closest('.code-block-wrap');
        const code = wrap ? wrap.querySelector('code') : null;
        if (code) {
          navigator.clipboard.writeText(code.innerText).then(() => {
            const orig = btn.innerText;
            btn.innerText = 'Copied!';
            btn.style.background = 'var(--accent)';
            btn.style.color = 'white';
            setTimeout(() => {
              btn.innerText = orig;
              btn.style.background = '';
              btn.style.color = '';
            }, 2000);
          });
        }
      });
    });

    // 5. Instant Filter / Search & Language Sorting
    const searchInput = document.getElementById('search-input');
    const cards = document.querySelectorAll('.grid .card, .video-grid .video-card');
    const filterTags = document.querySelectorAll('.filter-tag');

    let currentFilter = 'all';

    function applyFilter() {
      const q = (searchInput ? searchInput.value : '').toLowerCase().trim();
      cards.forEach(card => {
        const text = card.innerText.toLowerCase();
        const domain = (card.querySelector('.card-domain')?.innerText || '').toLowerCase();
        
        const matchesQuery = !q || text.includes(q);
        const matchesTag = currentFilter === 'all' || 
                           card.classList.contains(currentFilter) || 
                           domain.includes(currentFilter.replace('tag-', '').replace('lang-', '')) || 
                           text.includes(currentFilter.replace('tag-', '').replace('lang-', ''));
        
        if (matchesQuery && matchesTag) {
          card.style.display = '';
        } else {
          card.style.display = 'none';
        }
      });
    }

    if (searchInput) {
      searchInput.addEventListener('input', applyFilter);
    }

    filterTags.forEach(tag => {
      tag.addEventListener('click', () => {
        filterTags.forEach(t => t.classList.remove('active'));
        tag.classList.add('active');
        currentFilter = tag.getAttribute('data-filter') || 'all';
        applyFilter();
      });
    });

    // 6. 100% Wide Book Reader Controls
    const pageSelect = document.getElementById('book-page-select');
    const readerContainer = document.querySelector('.book-reader-container');
    const widthBtns = document.querySelectorAll('[data-reader-width]');

    if (pageSelect) {
      pageSelect.addEventListener('change', (e) => {
        const targetPage = document.getElementById(e.target.value);
        if (targetPage) {
          const headerOffset = 130;
          const elPos = targetPage.getBoundingClientRect().top;
          const offsetPos = elPos + window.pageYOffset - headerOffset;
          window.scrollTo({ top: offsetPos, behavior: 'smooth' });
        }
      });

      // Update dropdown selection as user scrolls
      const pageElements = document.querySelectorAll('.book-page-wrapper');
      if (pageElements.length > 0) {
        const pageObserver = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting && entry.target.id) {
              pageSelect.value = entry.target.id;
            }
          });
        }, { rootMargin: '-100px 0px -60% 0px' });

        pageElements.forEach(el => pageObserver.observe(el));
      }
    }

    if (widthBtns.length > 0 && readerContainer) {
      widthBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          widthBtns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const widthClass = btn.getAttribute('data-reader-width');
          readerContainer.className = 'book-reader-container ' + widthClass;
        });
      });
    }
  });

  function updateToggleText(btn, theme) {
    btn.innerHTML = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
  }
})();
