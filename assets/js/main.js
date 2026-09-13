/* ============================================================
   Equity Education Thailand — main.js (v2.0)
   Vanilla JS · no dependencies
   ============================================================ */
(function () {
  'use strict';

  const $  = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- 1. Theme ---------- */
  const THEME_KEY = 'eet-theme';
  const root = document.documentElement;

  function applyTheme(t) {
    root.setAttribute('data-theme', t);
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', t === 'dark' ? '#0b1220' : '#1a2b4c');
    const toggle = $('#themeToggle');
    if (toggle) {
      toggle.setAttribute('aria-pressed', String(t === 'dark'));
      toggle.setAttribute('aria-label', t === 'dark' ? 'สลับเป็นโหมดสว่าง' : 'สลับเป็นโหมดมืด');
    }
    document.dispatchEvent(new CustomEvent('eet:themechange', { detail: { theme: t } }));
  }
  const saved = localStorage.getItem(THEME_KEY);
  applyTheme(saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));

  const themeToggle = $('#themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      localStorage.setItem(THEME_KEY, next);
    });
  }

  /* ---------- 2. Mobile nav ---------- */
  const navToggle = $('#navToggle');
  const mainNav   = $('#mainNav');
  function setNavOpen(open) {
    if (!mainNav || !navToggle) return;
    mainNav.classList.toggle('is-open', open);
    navToggle.setAttribute('aria-expanded', String(open));
    navToggle.setAttribute('aria-label', open ? 'ปิดเมนู' : 'เปิดเมนู');
    document.body.classList.toggle('nav-open', open);
  }
  if (navToggle && mainNav) {
    navToggle.addEventListener('click', () => {
      setNavOpen(!mainNav.classList.contains('is-open'));
    });
    mainNav.addEventListener('click', e => {
      if (e.target.tagName === 'A') setNavOpen(false);
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && mainNav.classList.contains('is-open')) {
        setNavOpen(false);
        navToggle.focus();
      }
    });
  }

  /* ---------- 3. Scroll effects ---------- */
  const header   = $('#siteHeader');
  const progress = $('#scrollProgress');
  const toTop    = $('#toTop');
  let ticking = false;

  function onScroll() {
    const y   = window.scrollY;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    if (header)   header.classList.toggle('is-scrolled', y > 12);
    if (progress) progress.style.width = max > 0 ? (y / max) * 100 + '%' : '0%';
    if (toTop)    toTop.classList.toggle('is-visible', y > 620);
    ticking = false;
  }
  window.addEventListener('scroll', () => {
    if (!ticking) { window.requestAnimationFrame(onScroll); ticking = true; }
  }, { passive: true });
  onScroll();

  if (toTop) toTop.addEventListener('click', () =>
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }));

  /* ---------- 4. Reveal on scroll ---------- */
  const revealEls = $$('.reveal');
  if (revealEls.length) {
    if (reduceMotion || !('IntersectionObserver' in window)) {
      revealEls.forEach(el => el.classList.add('is-in'));
    } else {
      const ro = new IntersectionObserver((entries) => {
        entries.forEach((en, i) => {
          if (en.isIntersecting) {
            setTimeout(() => en.target.classList.add('is-in'), i * 70);
            ro.unobserve(en.target);
          }
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' });
      revealEls.forEach(el => ro.observe(el));
    }
  }

  /* ---------- 5. Animated bars ---------- */
  const ratioCard = $('#ratioCard');
  if (ratioCard) {
    const fire = () => $$('.bar', ratioCard).forEach(b => { b.style.width = b.dataset.w + '%'; });
    if (reduceMotion || !('IntersectionObserver' in window)) fire();
    else {
      const bo = new IntersectionObserver(en => {
        if (en[0].isIntersecting) { setTimeout(fire, 260); bo.disconnect(); }
      }, { threshold: 0.3 });
      bo.observe(ratioCard);
    }
  }

  /* ---------- 6. Counters ---------- */
  const counted = new WeakSet();
  function runCounter(el) {
    if (counted.has(el)) return;
    counted.add(el);
    const target = parseFloat(el.dataset.target) || 0;
    if (reduceMotion) { el.textContent = target.toLocaleString('th-TH'); return; }
    const dur = 1700, t0 = performance.now();
    function step(now) {
      const p = Math.min((now - t0) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.floor(target * eased).toLocaleString('th-TH');
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target.toLocaleString('th-TH');
    }
    requestAnimationFrame(step);
  }
  function bindCounters(nodes) {
    const list = Array.from(nodes || []);
    if (!list.length) return;
    if (!('IntersectionObserver' in window)) { list.forEach(runCounter); return; }
    const co = new IntersectionObserver(en => {
      en.forEach(e => { if (e.isIntersecting) { runCounter(e.target); co.unobserve(e.target); } });
    }, { threshold: 0.5 });
    list.forEach(c => co.observe(c));
  }
  bindCounters($$('.counter'));

  /* ---------- 7. Tabs (WAI-ARIA Tabs) ---------- */
  const tabWrap = $('#conceptTabs');
  if (tabWrap) {
    const btns   = $$('[role="tab"]', tabWrap);
    const panels = $$('[role="tabpanel"]', tabWrap);
    const list   = $('[role="tablist"]', tabWrap);
    if (list) list.setAttribute('aria-orientation', 'horizontal');
    function activate(key, focus) {
      btns.forEach(b => {
        const on = b.dataset.tab === key;
        b.setAttribute('aria-selected', String(on));
        b.tabIndex = on ? 0 : -1;
      });
      panels.forEach(p => {
        const on = p.dataset.panel === key;
        p.classList.toggle('is-active', on);
        p.hidden = !on;
      });
      if (focus) { const b = btns.find(x => x.dataset.tab === key); if (b) b.focus(); }
    }
    const initial = (btns.find(b => b.getAttribute('aria-selected') === 'true') || btns[0]).dataset.tab;
    activate(initial);
    btns.forEach(b => b.addEventListener('click', () => activate(b.dataset.tab)));
    tabWrap.addEventListener('keydown', e => {
      if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(e.key)) return;
      const i = btns.findIndex(b => b.getAttribute('aria-selected') === 'true');
      let n = i;
      if (e.key === 'ArrowRight') n = (i + 1) % btns.length;
      if (e.key === 'ArrowLeft')  n = (i - 1 + btns.length) % btns.length;
      if (e.key === 'Home') n = 0;
      if (e.key === 'End')  n = btns.length - 1;
      e.preventDefault();
      activate(btns[n].dataset.tab, true);
    });
  }

  /* ---------- 8. Accordion — single open ---------- */
  const acc = $('#debateAcc');
  if (acc) {
    $$('details', acc).forEach(d => {
      d.addEventListener('toggle', () => {
        if (d.open) $$('details', acc).forEach(o => { if (o !== d) o.open = false; });
      });
    });
  }

  /* ---------- 9. Scrollspy ---------- */
  const spyTargets = $$('section[id], .rsec[id]');
  const spyLinks   = $$('.main-nav a[href^="#"], .toc-list a[href^="#"]');
  if (spyTargets.length && spyLinks.length && 'IntersectionObserver' in window) {
    const so = new IntersectionObserver(entries => {
      entries.forEach(en => {
        if (!en.isIntersecting) return;
        const id = en.target.id;
        spyLinks.forEach(l => l.classList.toggle('is-active', l.getAttribute('href') === '#' + id));
      });
    }, { rootMargin: '-25% 0px -68% 0px' });
    spyTargets.forEach(t => so.observe(t));
  }

  /* ---------- 10. TOC search ---------- */
  const tocSearch = $('#tocSearch');
  if (tocSearch) {
    tocSearch.addEventListener('input', () => {
      const q = tocSearch.value.trim().toLowerCase();
      $$('.toc-list a').forEach(a => {
        a.classList.toggle('is-hidden', q !== '' && !a.textContent.toLowerCase().includes(q));
      });
    });
  }

  const tocDrawer = $('.toc-drawer');
  if (tocDrawer) {
    const desktopToc = window.matchMedia('(min-width: 1001px)');
    const syncToc = () => { if (desktopToc.matches) tocDrawer.open = true; };
    desktopToc.addEventListener('change', syncToc);
    syncToc();
  }

  const printReport = $('#printReport');
  if (printReport) printReport.addEventListener('click', () => window.print());

  /* ---------- 11. Copy citation ---------- */
  const copyBtn = $('#copyCite');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const txt = $('#citeText').innerText.trim();
      try {
        await navigator.clipboard.writeText(txt);
        const old = copyBtn.textContent;
        copyBtn.textContent = '✓ คัดลอกแล้ว';
        setTimeout(() => (copyBtn.textContent = old), 2000);
      } catch { alert('กรุณาคัดลอกด้วยตนเอง:\n\n' + txt); }
    });
  }

  /* ---------- 12. Smooth anchor with header offset ---------- */
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;
    const id = a.getAttribute('href');
    if (id === '#' || id.length < 2) return;
    const el = document.querySelector(id);
    if (!el) return;
    e.preventDefault();
    const top = el.getBoundingClientRect().top + window.scrollY - (header ? header.offsetHeight + 18 : 18);
    window.scrollTo({ top, behavior: reduceMotion ? 'auto' : 'smooth' });
    history.replaceState(null, '', id);
  });

  /* ---------- 13. Shared helpers (ใช้โดย simulator / gap-map / หน้าแรก) ---------- */
  const CORE_KEYS = ['primary_opec', 'secondary_ope'];

  function summariseUnits(list) {
    const deficits = list.filter(u => u.gap > 0);
    const surpluses = list.filter(u => u.gap < 0);
    const deficit = deficits.reduce((s, u) => s + u.gap, 0);
    const surplus = Math.abs(surpluses.reduce((s, u) => s + u.gap, 0));
    return {
      deficit, surplus, net: deficit - surplus,
      primary: list.find(u => u.key === 'primary_opec'),
      secondary: list.find(u => u.key === 'secondary_ope')
    };
  }

  window.EET = {
    fmt: n => Math.round(n).toLocaleString('th-TH'),
    reduceMotion,
    CORE_KEYS,
    runCounter,
    bindCounters,
    chartColors() {
      const dark = root.getAttribute('data-theme') === 'dark';
      return { grid: dark ? '#233149' : '#e2e8f1', text: dark ? '#a9b6c9' : '#4a5769' };
    },
    /* ข้อมูลสำรองจาก 11.xlsx — ปีการศึกษา 2569 · รายชั้นไม่รวมศูนย์ กศ.พิเศษ */
    FALLBACK: {
      meta: {
        title: 'ตารางที่ 11 จำนวนนักเรียนและห้องเรียน จำแนกตามประเภทโรงเรียน รายชั้น',
        source: 'สำนักงานคณะกรรมการการศึกษาขั้นพื้นฐาน (สพฐ.)',
        academic_year: 2569, teacher_ratio: 20,
        coverage_note: 'ครอบคลุมเฉพาะสถานศึกษาสังกัด สพฐ. ไม่รวม อปท. เอกชน และสังกัดอื่น',
        grades_note: 'รายชั้นรวม สพป. สพม. การศึกษาสงเคราะห์ และการศึกษาพิเศษ ไม่รวมศูนย์การศึกษาพิเศษ',
        core_keys: CORE_KEYS
      },
      national: [
        { key:'primary_opec',  name_th:'ประถมศึกษา (สพป.)',  short:'สพป.',          students:3843825, classrooms:263359 },
        { key:'secondary_ope', name_th:'มัธยมศึกษา (สพม.)',  short:'สพม.',          students:2251217, classrooms:69704 },
        { key:'welfare',       name_th:'การศึกษาสงเคราะห์',   short:'กศ.สงเคราะห์',  students:34725,   classrooms:2551 },
        { key:'special_ed',    name_th:'การศึกษาพิเศษ',       short:'กศ.พิเศษ',      students:12762,   classrooms:4731 },
        { key:'special_ctr',   name_th:'ศูนย์การศึกษาพิเศษ',  short:'ศูนย์ กศ.พิเศษ', students:30311,   classrooms:7702 }
      ],
      grand_total: { students:6172840, classrooms:348047 },
      grades: [
        { label:'อนุบาล 1',                     level:'ปฐมวัย', students:66636,  classrooms:7077 },
        { label:'อนุบาล 2',                     level:'ปฐมวัย', students:303288, classrooms:27107 },
        { label:'อนุบาล 3',                     level:'ปฐมวัย', students:334747, classrooms:27816 },
        { label:'ประถมศึกษาปีที่ 1',            level:'ประถม',  students:410425, classrooms:29829 },
        { label:'ประถมศึกษาปีที่ 2',            level:'ประถม',  students:433610, classrooms:29923 },
        { label:'ประถมศึกษาปีที่ 3',            level:'ประถม',  students:449855, classrooms:30077 },
        { label:'ประถมศึกษาปีที่ 4',            level:'ประถม',  students:450380, classrooms:30020 },
        { label:'ประถมศึกษาปีที่ 5',            level:'ประถม',  students:462565, classrooms:30075 },
        { label:'ประถมศึกษาปีที่ 6',            level:'ประถม',  students:475740, classrooms:30373 },
        { label:'มัธยมศึกษาปีที่ 1',            level:'ม.ต้น',  students:554262, classrooms:20544 },
        { label:'มัธยมศึกษาปีที่ 2',            level:'ม.ต้น',  students:574735, classrooms:20757 },
        { label:'มัธยมศึกษาปีที่ 3',            level:'ม.ต้น',  students:552600, classrooms:20551 },
        { label:'มัธยมศึกษาปีที่ 4 หรือ เทียบเท่า', level:'ม.ปลาย', students:375959, classrooms:12264 },
        { label:'มัธยมศึกษาปีที่ 5 หรือ เทียบเท่า', level:'ม.ปลาย', students:354681, classrooms:12102 },
        { label:'มัธยมศึกษาปีที่ 6 หรือ เทียบเท่า', level:'ม.ปลาย', students:343046, classrooms:11836 }
      ]
    },
    FALLBACK_FACTS: {
      facts: {
        budget_moe_2569: {
          value: 355014, label: 'งบประมาณกระทรวงศึกษาธิการ ปี 2569 (หลังสภาปรับลด)',
          confidence: 'high', as_of: 'พ.ร.บ.งบประมาณรายจ่ายประจำปีงบประมาณ พ.ศ. 2569',
          note: 'ร่างเดิม 355,108 ล้านบาท อันดับ 3 ของประเทศ หลังสภาปรับลดเหลือ 355,014 ล้านบาท',
          sources: [
            { title: 'สำนักงานปลัด ศธ. — งบประมาณปี 2569', url: 'https://ops.moe.go.th/budget-moe69-30052025/' },
            { title: 'แนวหน้า — งบ ศธ. หลังสภาปรับลด', url: 'https://www.naewna.com/local/907460' }
          ]
        },
        oosc_2566: {
          value: 1025514, label: 'เด็กและเยาวชนนอกระบบการศึกษา อายุ 3–18 ปี',
          confidence: 'high', as_of: 'ปีการศึกษา 2566 · กสศ.',
          sources: [
            { title: 'กสศ. — ที่มาของตัวเลข 1.02 ล้านคน', url: 'https://flexiblelearning.eef.or.th/infographic-number-102/' }
          ]
        },
        new_dropouts_2568: {
          value: 189977, label: 'เด็กหลุดออกจากระบบรายใหม่ ปี 2568',
          confidence: 'mid', as_of: 'ปี 2568 · กสศ. อ้างใน Thai PBS Policy Watch',
          sources: [
            { title: 'Thai PBS Policy Watch', url: 'https://policywatch.thaipbs.or.th/article/education-58' }
          ]
        },
        equity_scholarships_2569: {
          value: 1300000, label: 'นักเรียนยากจนพิเศษที่ กสศ. ตั้งเป้าให้ทุนเสมอภาค ปี 2569',
          confidence: 'high', as_of: 'ปีการศึกษา 2569',
          note: 'กว่า 1.3 ล้านคน · 4,200 บาท/คน/ปี',
          sources: [
            { title: 'The Active — ทุนเสมอภาคปี 2569', url: 'https://theactive.thaipbs.or.th/news/learning-education-20260529' }
          ]
        }
      },
      laws: {
        constitution_2560: {
          title: 'รัฐธรรมนูญแห่งราชอาณาจักรไทย พุทธศักราช 2560',
          url: 'https://www.ratchakitcha.soc.go.th/DATA/PDF/2560/A/040/1.PDF',
          articles: 'มาตรา 4, 27, 51, 54, 258 จ., 261'
        },
        education_act_2542: {
          title: 'พระราชบัญญัติการศึกษาแห่งชาติ พ.ศ. 2542',
          url: 'https://www.onesqa.or.th/upload/download/file_975dff739ff5a909753b8bff237c78fa.pdf',
          articles: 'มาตรา 9, 10, 17, 39, 47–51, 58, 60'
        },
        eef_act_2561: {
          title: 'พระราชบัญญัติกองทุนเพื่อความเสมอภาคทางการศึกษา พ.ศ. 2561',
          url: 'https://www.eef.or.th/wp-content/uploads/2022/04/eef-GovernmentGazette.pdf',
          articles: 'มาตรา 5, 6, 8, 14, 18, 23, 24, 44'
        }
      },
      other: {
        pisa_2022: {
          title: 'OECD — PISA 2022 Results (Volume I)',
          url: 'https://www.oecd.org/en/publications/pisa-2022-results-volume-i_53f23881-en.html'
        }
      }
    },
    sourceLinks(item) {
      const src = (item && item.sources) || (item && item.url ? [item] : []);
      return src.map(s => `<a href="${s.url}" target="_blank" rel="noopener">${s.title}</a>`).join(' · ');
    },
    units(data, opts) {
      const scope = (opts && opts.scope) || 'all';
      const ratio = (data.meta && data.meta.teacher_ratio) || 20;
      const allow = scope === 'core' ? CORE_KEYS : null;
      return (data.national || [])
        .filter(u => u.key !== 'total' && u.classrooms)
        .filter(u => !allow || allow.includes(u.key))
        .map(u => {
          const ruleA = u.students / ratio;
          const ruleB = u.classrooms;
          const gap = ruleB - ruleA;
          return {
            ...u,
            short: u.short || u.name_th,
            spr: u.students / u.classrooms,
            ruleA, ruleB, gap,
            core: CORE_KEYS.includes(u.key)
          };
        });
    },
    analyse(data) {
      const coreList = this.units(data, { scope: 'core' });
      const allList  = this.units(data, { scope: 'all' });
      return {
        ratio: (data.meta && data.meta.teacher_ratio) || 20,
        core: { list: coreList, ...summariseUnits(coreList) },
        all:  { list: allList,  ...summariseUnits(allList) }
      };
    },
    async loadData() {
      try {
        const r = await fetch('assets/data/school-data.json', { cache: 'no-store' });
        if (r.ok) {
          const j = await r.json();
          if (j.national && j.national.length) {
            j.national = j.national
              .filter(n => n.key !== 'total' && n.classrooms)
              .map(n => ({ ...n, short: n.short || (n.name_th || '').replace(/[()]/g, '').split(' ').pop() }));
            return j;
          }
        }
      } catch (e) { /* fallthrough */ }
      return this.FALLBACK;
    },
    async loadFacts() {
      try {
        const r = await fetch('assets/data/facts.json', { cache: 'no-store' });
        if (r.ok) {
          const j = await r.json();
          if (j.facts) return j;
        }
      } catch (e) { /* fallthrough */ }
      return this.FALLBACK_FACTS;
    },
    setCounter(el, value) {
      if (!el || value == null || Number.isNaN(Number(value))) return;
      const n = Math.round(Number(value));
      el.dataset.target = String(n);
      if (counted.has(el)) el.textContent = n.toLocaleString('th-TH');
    },
    async hydrateHome() {
      const rootEl = document.getElementById('data');
      if (!rootEl) return;
      const [data, pack] = await Promise.all([this.loadData(), this.loadFacts()]);
      const a = this.analyse(data);
      const facts = pack.facts || {};
      const students = data.grand_total && data.grand_total.students;
      this.setCounter($('[data-fact="students"]'), students);
      this.setCounter($('[data-fact="teacher_core_deficit"]'), a.core.deficit);
      this.setCounter($('[data-fact="budget_moe_2569"]'), facts.budget_moe_2569 && facts.budget_moe_2569.value);
      this.setCounter($('[data-fact="oosc_2566"]'), facts.oosc_2566 && facts.oosc_2566.value);
      this.setCounter($('[data-fact="new_dropouts_2568"]'), facts.new_dropouts_2568 && facts.new_dropouts_2568.value);
      this.setCounter($('[data-fact="equity_scholarships_2569"]'), facts.equity_scholarships_2569 && facts.equity_scholarships_2569.value);

      const allDef = Math.round(a.all.deficit);
      const note = $('[data-teacher-note]');
      if (note) {
        note.innerHTML = `ระบบหลักขาด <b>${this.fmt(a.core.deficit)}</b> ที่ สพป. หากใช้โมเดล 1:20 กับทุกประเภทจะได้ <b>${this.fmt(allDef)}</b> ซึ่งรวม กศ.พิเศษที่มีคน/ห้องต่ำโดยเจตนา — <a href="gap-map.html">ดูแผนที่ช่องว่าง</a>`;
      }
      $$('[data-src]').forEach(el => {
        const item = facts[el.dataset.src];
        if (item) el.innerHTML = this.sourceLinks(item);
      });
    }
  };

  if (document.getElementById('data')) {
    const start = () => window.EET.hydrateHome();
    document.readyState === 'loading'
      ? document.addEventListener('DOMContentLoaded', start) : start();
  }

})();