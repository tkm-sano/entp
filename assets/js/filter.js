document.addEventListener("DOMContentLoaded", () => {
  const cards = Array.from(document.querySelectorAll(".model-card"));
  const resultCount = document.getElementById("filterResultCount");
  const pagination = document.getElementById("modelPagination");
  const PAGE_SIZE = 15;
  let currentPage = 1;

  function toNumber(value) {
    const n = parseInt(value || "", 10);
    return Number.isFinite(n) ? n : null;
  }

  const filters = {
    gender: "all",
    tags: new Set(),
    heightMin: 150,
    heightMax: 200,
    ageMin: 18,
    ageMax: 24
  };

  const tagAliases = {
    "インフルエンサー": ["インフルエンサー", "influencer"],
    "ミス": ["ミス", "miss"],
    "ミスター": ["ミスター", "mister", "mr"],
    "可愛い系": ["可愛い系", "かわいい系", "kawaii", "cute"],
    "綺麗系": ["綺麗系", "きれい系", "beauty", "beautiful"],
    "清楚系": ["清楚系", "seiso"],
    "草食系": ["草食系", "soushoku"],
    "犬系": ["犬系", "inu", "dog"]
  };

  const heightMinInput = document.querySelector('[data-filter="height-min"]');
  const heightMaxInput = document.querySelector('[data-filter="height-max"]');
  const ageMinInput = document.querySelector('[data-filter="age-min"]');
  const ageMaxInput = document.querySelector('[data-filter="age-max"]');

  const heightMinLabel = document.querySelector('[data-range-label="height-min"]');
  const heightMaxLabel = document.querySelector('[data-range-label="height-max"]');
  const ageMinLabel = document.querySelector('[data-range-label="age-min"]');
  const ageMaxLabel = document.querySelector('[data-range-label="age-max"]');

  function getRangeFromCards(datasetValues, fallbackMin, fallbackMax) {
    if (datasetValues.length === 0) {
      return { min: fallbackMin, max: fallbackMax };
    }
    return {
      min: Math.min(...datasetValues),
      max: Math.max(...datasetValues)
    };
  }

  function initializeRangesFromCards() {
    const heights = cards
      .map(card => toNumber(card.dataset.height))
      .filter(value => value !== null);
    const ages = cards
      .map(card => toNumber(card.dataset.age))
      .filter(value => value !== null);

    const heightRange = getRangeFromCards(heights, filters.heightMin, filters.heightMax);
    const ageRange = getRangeFromCards(ages, filters.ageMin, filters.ageMax);

    filters.heightMin = heightRange.min;
    filters.heightMax = heightRange.max;
    filters.ageMin = ageRange.min;
    filters.ageMax = ageRange.max;

    if (heightMinInput && heightMaxInput) {
      heightMinInput.min = String(heightRange.min);
      heightMinInput.max = String(heightRange.max);
      heightMaxInput.min = String(heightRange.min);
      heightMaxInput.max = String(heightRange.max);
      heightMinInput.value = String(heightRange.min);
      heightMaxInput.value = String(heightRange.max);
    }

    if (ageMinInput && ageMaxInput) {
      ageMinInput.min = String(ageRange.min);
      ageMinInput.max = String(ageRange.max);
      ageMaxInput.min = String(ageRange.min);
      ageMaxInput.max = String(ageRange.max);
      ageMinInput.value = String(ageRange.min);
      ageMaxInput.value = String(ageRange.max);
    }
  }

  function normalizeTag(tag) {
    return tag.trim().toLowerCase();
  }

  function updateRangeLabels() {
    if (heightMinLabel) heightMinLabel.textContent = String(filters.heightMin);
    if (heightMaxLabel) heightMaxLabel.textContent = String(filters.heightMax);
    if (ageMinLabel) ageMinLabel.textContent = String(filters.ageMin);
    if (ageMaxLabel) ageMaxLabel.textContent = String(filters.ageMax);
  }

  function getMatchedCards() {
    return cards.filter(card => {
      const cardHeight = toNumber(card.dataset.height) ?? 0;
      const cardAge = toNumber(card.dataset.age) ?? 0;
      const cardTags = (card.dataset.tags || "")
        .split(",")
        .map(normalizeTag)
        .filter(Boolean);

      const genderMatch =
        filters.gender === "all" || card.dataset.gender === filters.gender;

      const heightMatch =
        cardHeight >= filters.heightMin && cardHeight <= filters.heightMax;

      const ageMatch =
        cardAge >= filters.ageMin && cardAge <= filters.ageMax;

      const tagMatch =
        filters.tags.size === 0 ||
        [...filters.tags].every(tag => {
          const aliases = (tagAliases[tag] || [tag]).map(normalizeTag);
          return aliases.some(alias => cardTags.includes(alias));
        });

      return genderMatch && heightMatch && ageMatch && tagMatch;
    });
  }

  function updateResultCount(total) {
    if (!resultCount) return;
    resultCount.textContent = `該当 ${total} 人`;
  }

  function renderPagination(totalPages) {
    if (!pagination) return;

    if (totalPages <= 1) {
      pagination.innerHTML = "";
      return;
    }

    pagination.innerHTML = `
      <button type="button" class="pagination-btn" data-page-action="prev">前へ</button>
      <span class="pagination-info">${currentPage} / ${totalPages}</span>
      <button type="button" class="pagination-btn" data-page-action="next">次へ</button>
    `;

    const prev = pagination.querySelector('[data-page-action="prev"]');
    const next = pagination.querySelector('[data-page-action="next"]');

    if (prev) {
      prev.disabled = currentPage <= 1;
      prev.addEventListener("click", () => {
        currentPage = Math.max(1, currentPage - 1);
        filterCards(false);
      });
    }

    if (next) {
      next.disabled = currentPage >= totalPages;
      next.addEventListener("click", () => {
        currentPage = Math.min(totalPages, currentPage + 1);
        filterCards(false);
      });
    }
  }

  function filterCards(resetPage = true) {
    if (resetPage) currentPage = 1;

    const matchedCards = getMatchedCards();
    const total = matchedCards.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    currentPage = Math.min(currentPage, totalPages);

    const start = (currentPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    const visibleCards = new Set(matchedCards.slice(start, end));

    cards.forEach(card => {
      card.classList.toggle("hidden", !visibleCards.has(card));
    });

    updateResultCount(total);
    renderPagination(totalPages);
  }

  function bindGenderEvents() {
    document.querySelectorAll('[data-filter="gender"]').forEach(btn => {
      btn.addEventListener("click", () => {
        filters.gender = btn.dataset.value;

        document
          .querySelectorAll('[data-filter="gender"]')
          .forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        filterCards();
      });
    });
  }

  function bindTagEvents() {
    document.querySelectorAll('[data-filter="tag"]').forEach(btn => {
      btn.addEventListener("click", () => {
        const value = normalizeTag(btn.dataset.value || "");

        if (!value) return;

        if (filters.tags.has(value)) {
          filters.tags.delete(value);
          btn.classList.remove("active");
        } else {
          filters.tags.add(value);
          btn.classList.add("active");
        }

        filterCards();
      });
    });
  }

  function bindRangeEvents() {
    if (heightMinInput && heightMaxInput) {
      heightMinInput.addEventListener("input", () => {
        const next = parseInt(heightMinInput.value, 10);
        filters.heightMin = Math.min(next, filters.heightMax);
        heightMinInput.value = String(filters.heightMin);
        updateRangeLabels();
        filterCards();
      });

      heightMaxInput.addEventListener("input", () => {
        const next = parseInt(heightMaxInput.value, 10);
        filters.heightMax = Math.max(next, filters.heightMin);
        heightMaxInput.value = String(filters.heightMax);
        updateRangeLabels();
        filterCards();
      });
    }

    if (ageMinInput && ageMaxInput) {
      ageMinInput.addEventListener("input", () => {
        const next = parseInt(ageMinInput.value, 10);
        filters.ageMin = Math.min(next, filters.ageMax);
        ageMinInput.value = String(filters.ageMin);
        updateRangeLabels();
        filterCards();
      });

      ageMaxInput.addEventListener("input", () => {
        const next = parseInt(ageMaxInput.value, 10);
        filters.ageMax = Math.max(next, filters.ageMin);
        ageMaxInput.value = String(filters.ageMax);
        updateRangeLabels();
        filterCards();
      });
    }
  }

  bindGenderEvents();
  bindTagEvents();
  bindRangeEvents();
  initializeRangesFromCards();
  updateRangeLabels();
  filterCards();
});
