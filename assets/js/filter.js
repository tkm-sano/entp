document.addEventListener("DOMContentLoaded", () => {
  const cards = Array.from(document.querySelectorAll(".model-card"));
  const resultCount = document.getElementById("filterResultCount");
  const pagination = document.getElementById("modelPagination");

  const filterSheet = document.getElementById("filtersSheet");
  const filterBackdrop = document.querySelector(".filters-sheet-backdrop");
  const openSheetBtn = document.querySelector('[data-filter-action="open-sheet"]');
  const applyBtn = document.querySelector('[data-filter-action="apply"]');
  const resetBtn = document.querySelector('[data-filter-action="reset"]');
  const closeSheetBtns = document.querySelectorAll('[data-filter-action="close-sheet"]');
  const mobileFilterCount = document.getElementById("mobileFilterCount");

  const genderSelect = document.querySelector('[data-filter-select="gender"]');
  const tagCheckboxes = document.querySelectorAll("[data-filter-tag]");
  const heightMinSelect = document.querySelector('[data-filter-select="height-min"]');
  const heightMaxSelect = document.querySelector('[data-filter-select="height-max"]');
  const ageMinSelect = document.querySelector('[data-filter-select="age-min"]');
  const ageMaxSelect = document.querySelector('[data-filter-select="age-max"]');

  const PAGE_SIZE = 18;
  let currentPage = 1;
  let isSheetOpen = false;

  const tagAliases = [
    ["インフルエンサー", "influencer"],
    ["ミス", "miss"],
    ["ミスター", "mister", "mr"],
    ["可愛い系", "かわいい系", "kawaii", "cute"],
    ["綺麗系", "きれい系", "beauty", "beautiful"],
    ["清楚系", "seiso"],
    ["草食系", "soushoku"],
    ["犬系", "inu", "dog"]
  ];

  const filters = {
    gender: "all",
    tags: new Set(),
    heightMin: 0,
    heightMax: 0,
    ageMin: 0,
    ageMax: 0
  };

  const filterDefaults = {
    heightMin: 0,
    heightMax: 0,
    ageMin: 0,
    ageMax: 0
  };

  function normalizeTag(tag) {
    return String(tag || "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "");
  }

  function getTagCandidates(tag) {
    const normalizedTag = normalizeTag(tag);
    if (!normalizedTag) return [];

    const aliasGroup = tagAliases.find(group =>
      group.map(normalizeTag).includes(normalizedTag)
    );

    if (!aliasGroup) return [normalizedTag];
    return aliasGroup.map(normalizeTag);
  }

  function toNumber(value) {
    const n = parseInt(value || "", 10);
    return Number.isFinite(n) ? n : null;
  }

  function getRangeFromCards(values, fallbackMin, fallbackMax) {
    if (values.length === 0) {
      return { min: fallbackMin, max: fallbackMax };
    }
    return {
      min: Math.min(...values),
      max: Math.max(...values)
    };
  }

  function fillRangeSelectOptions(selectEl, min, max, unit) {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    for (let v = min; v <= max; v += 1) {
      const option = document.createElement("option");
      option.value = String(v);
      option.textContent = `${v}${unit}`;
      selectEl.appendChild(option);
    }
  }

  function initializeRangeSelects() {
    const heights = cards
      .map(card => toNumber(card.dataset.height))
      .filter(value => value !== null);
    const ages = cards
      .map(card => toNumber(card.dataset.age))
      .filter(value => value !== null);

    const heightRange = getRangeFromCards(heights, 150, 200);
    const ageRange = getRangeFromCards(ages, 18, 24);

    filterDefaults.heightMin = heightRange.min;
    filterDefaults.heightMax = heightRange.max;
    filterDefaults.ageMin = ageRange.min;
    filterDefaults.ageMax = ageRange.max;

    filters.heightMin = heightRange.min;
    filters.heightMax = heightRange.max;
    filters.ageMin = ageRange.min;
    filters.ageMax = ageRange.max;

    fillRangeSelectOptions(heightMinSelect, heightRange.min, heightRange.max, "cm");
    fillRangeSelectOptions(heightMaxSelect, heightRange.min, heightRange.max, "cm");
    fillRangeSelectOptions(ageMinSelect, ageRange.min, ageRange.max, "歳");
    fillRangeSelectOptions(ageMaxSelect, ageRange.min, ageRange.max, "歳");

    if (heightMinSelect) heightMinSelect.value = String(filters.heightMin);
    if (heightMaxSelect) heightMaxSelect.value = String(filters.heightMax);
    if (ageMinSelect) ageMinSelect.value = String(filters.ageMin);
    if (ageMaxSelect) ageMaxSelect.value = String(filters.ageMax);
  }

  function getSelectedFilterCount() {
    let count = 0;
    if (filters.gender !== "all") count += 1;
    count += filters.tags.size;
    if (
      filters.heightMin !== filterDefaults.heightMin ||
      filters.heightMax !== filterDefaults.heightMax
    ) {
      count += 1;
    }
    if (
      filters.ageMin !== filterDefaults.ageMin ||
      filters.ageMax !== filterDefaults.ageMax
    ) {
      count += 1;
    }
    return count;
  }

  function updateMobileFilterCount() {
    if (!mobileFilterCount) return;
    mobileFilterCount.textContent = String(getSelectedFilterCount());
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

      const tagMatch = (() => {
        if (filters.tags.size === 0) return true;
        return [...filters.tags].every(tag => {
          const aliases = getTagCandidates(tag);
          return aliases.some(alias => cardTags.includes(alias));
        });
      })();

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
    updateMobileFilterCount();
  }

  function syncRangeFiltersFromSelects() {
    const nextHeightMin = toNumber(heightMinSelect && heightMinSelect.value);
    const nextHeightMax = toNumber(heightMaxSelect && heightMaxSelect.value);
    const nextAgeMin = toNumber(ageMinSelect && ageMinSelect.value);
    const nextAgeMax = toNumber(ageMaxSelect && ageMaxSelect.value);

    if (nextHeightMin !== null && nextHeightMax !== null) {
      filters.heightMin = Math.min(nextHeightMin, nextHeightMax);
      filters.heightMax = Math.max(nextHeightMin, nextHeightMax);
      if (heightMinSelect) heightMinSelect.value = String(filters.heightMin);
      if (heightMaxSelect) heightMaxSelect.value = String(filters.heightMax);
    }

    if (nextAgeMin !== null && nextAgeMax !== null) {
      filters.ageMin = Math.min(nextAgeMin, nextAgeMax);
      filters.ageMax = Math.max(nextAgeMin, nextAgeMax);
      if (ageMinSelect) ageMinSelect.value = String(filters.ageMin);
      if (ageMaxSelect) ageMaxSelect.value = String(filters.ageMax);
    }
  }

  function bindSelectEvents() {
    if (genderSelect) {
      genderSelect.addEventListener("change", () => {
        filters.gender = genderSelect.value || "all";
        filterCards();
      });
    }

    tagCheckboxes.forEach(checkbox => {
      checkbox.addEventListener("change", () => {
        const selectedTags = Array.from(tagCheckboxes)
          .filter(input => input.checked)
          .map(input => input.getAttribute("data-filter-tag"))
          .filter(Boolean);
        filters.tags = new Set(selectedTags);
        filterCards();
      });
    });

    [heightMinSelect, heightMaxSelect, ageMinSelect, ageMaxSelect].forEach(selectEl => {
      if (!selectEl) return;
      selectEl.addEventListener("change", () => {
        syncRangeFiltersFromSelects();
        filterCards();
      });
    });
  }

  function openFilterSheet() {
    if (!filterSheet || !filterBackdrop) return;
    if (!window.matchMedia("(max-width: 768px)").matches) return;
    isSheetOpen = true;
    filterSheet.classList.add("is-open");
    filterSheet.setAttribute("aria-hidden", "false");
    filterBackdrop.classList.add("is-open");
    document.body.classList.add("filters-open");
  }

  function closeFilterSheet() {
    if (!filterSheet || !filterBackdrop) return;
    isSheetOpen = false;
    filterSheet.classList.remove("is-open");
    filterBackdrop.classList.remove("is-open");
    document.body.classList.remove("filters-open");
    if (window.matchMedia("(max-width: 768px)").matches) {
      filterSheet.setAttribute("aria-hidden", "true");
    } else {
      filterSheet.setAttribute("aria-hidden", "false");
    }
  }

  function syncSheetAriaHidden() {
    if (!filterSheet || !filterBackdrop) return;
    if (window.matchMedia("(max-width: 768px)").matches) {
      filterSheet.setAttribute("aria-hidden", isSheetOpen ? "false" : "true");
    } else {
      isSheetOpen = false;
      filterSheet.classList.remove("is-open");
      filterBackdrop.classList.remove("is-open");
      document.body.classList.remove("filters-open");
      filterSheet.setAttribute("aria-hidden", "false");
    }
  }

  function resetFilters() {
    filters.gender = "all";
    filters.tags.clear();
    filters.heightMin = filterDefaults.heightMin;
    filters.heightMax = filterDefaults.heightMax;
    filters.ageMin = filterDefaults.ageMin;
    filters.ageMax = filterDefaults.ageMax;

    if (genderSelect) genderSelect.value = "all";
    tagCheckboxes.forEach(checkbox => {
      checkbox.checked = false;
    });
    if (heightMinSelect) heightMinSelect.value = String(filters.heightMin);
    if (heightMaxSelect) heightMaxSelect.value = String(filters.heightMax);
    if (ageMinSelect) ageMinSelect.value = String(filters.ageMin);
    if (ageMaxSelect) ageMaxSelect.value = String(filters.ageMax);

    filterCards();
  }

  function bindSheetEvents() {
    if (openSheetBtn) {
      openSheetBtn.addEventListener("click", openFilterSheet);
    }

    closeSheetBtns.forEach(btn => {
      btn.addEventListener("click", closeFilterSheet);
    });

    if (applyBtn) {
      applyBtn.addEventListener("click", () => {
        filterCards(false);
        closeFilterSheet();
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener("click", resetFilters);
    }

    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && isSheetOpen) {
        closeFilterSheet();
      }
    });

    window.addEventListener("resize", () => {
      syncSheetAriaHidden();
    });
  }

  initializeRangeSelects();
  bindSelectEvents();
  bindSheetEvents();
  syncSheetAriaHidden();
  filterCards();
});
