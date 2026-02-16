---
layout: default
title: TALENTS
permalink: /talents/
---

<section class="page-header">
  <h2>TALENT DATABASE</h2>
</section>

<!-- フィルター -->
<div class="filters" style="margin-bottom:20px; text-align:center;">
  <!-- 性別 -->
  <div>
    <strong>性別：</strong>
    <button class="filter-btn" data-filter="gender" data-value="all">All</button>
    <button class="filter-btn" data-filter="gender" data-value="male">男性</button>
    <button class="filter-btn" data-filter="gender" data-value="female">女性</button>
  </div>

  <!-- タグ -->
  <div style="margin-top:10px;">
    <strong>タグ：</strong>
    {% assign all_tags = site.talents | map: "tags" | join: "," | split: "," | uniq %}
    <button class="filter-btn" data-filter="tag" data-value="all">All</button>
    {% for tag in all_tags %}
    <button class="filter-btn" data-filter="tag" data-value="{{ tag | strip }}">{{ tag | strip }}</button>
    {% endfor %}
  </div>

  <!-- 身長 -->
  <div style="margin-top:10px;">
    <strong>身長：</strong>
    <button class="filter-btn" data-filter="height" data-value="all">All</button>
    <button class="filter-btn" data-filter="height" data-value="160-169">160-169cm</button>
    <button class="filter-btn" data-filter="height" data-value="170-179">170-179cm</button>
    <button class="filter-btn" data-filter="height" data-value="180-189">180-189cm</button>
  </div>
</div>

<section class="talent-grid">
  {% for t in site.talents %}
  <div class="talent-card" 
       data-gender="{{ t.gender | downcase }}" 
       data-tags="{{ t.tags | join: ',' | downcase }}" 
       data-height="{{ t.height }}"
       data-age="{{ t.age }}">
    <a href="{{ t.url | relative_url }}">
      <div class="image-wrapper">
        <img src="{{ t.images[0] | relative_url }}" alt="{{ t.name }}">
      </div>
      <div class="talent-info">
        <h3>{{ t.name }}</h3>
        <p>{{ t.kana }}</p>
        <p>{{ t.gender }} | {{ t.height }}cm | {{ t.age }}歳 | {{ t.tags | join: ', ' }}</p>
      </div>
    </a>
  </div>
  {% endfor %}
</section>

<!-- JSで複数条件絞り込み -->
<script>
let filters = {
  gender: 'all',
  tag: 'all',
  height: 'all',
  age: 'all'
};

function filterCards() {
  document.querySelectorAll('.talent-card').forEach(card => {
    let genderMatch = filters.gender === 'all' || card.dataset.gender === filters.gender;
    let tagMatch = filters.tag === 'all' || card.dataset.tags.split(',').includes(filters.tag.toLowerCase());
    let heightMatch = filters.height === 'all' || (() => {
      let h = parseInt(card.dataset.height);
      switch(filters.height) {
        case '160-169': return h >= 160 && h <= 169;
        case '170-179': return h >= 170 && h <= 179;
        case '180-189': return h >= 180 && h <= 189;
        default: return true;
      }
    })();
    let ageMatch = filters.age === 'all' || (() => {
      let a = parseInt(card.dataset.age);
      switch(filters.age) {
        case '20-29': return a >= 20 && a <= 29;
        case '30-39': return a >= 30 && a <= 39;
        case '40-49': return a >= 40 && a <= 49;
        default: return true;
      }
    })();

    card.style.display = (genderMatch && tagMatch && heightMatch && ageMatch) ? 'block' : 'none';
  });
}

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const filter = btn.dataset.filter;
    const value = btn.dataset.value.toLowerCase();
    filters[filter] = value;
    filterCards();
  });
});
</script>
