---
layout: default
title: MODEL DATABASE
---

<section class="page-header">
  <p class="page-header-eyebrow">MissConnect Curated Profiles</p>
  <h1>MODEL DATABASE</h1>
</section>

<!-- ================================
     FILTER INCLUDE
================================ -->
{% include filter.html %}

<div class="model-list-meta">
  <p id="filterResultCount">該当 0 人</p>
</div>

<!-- ================================
     MODEL GRID
================================ -->
<section class="model-grid">

  {% for t in site.models %}
    {% include model-card.html model=t %}
  {% endfor %}

</section>

<nav class="pagination" id="modelPagination" aria-label="モデル一覧ページネーション"></nav>

<!-- ================================
     FILTER SCRIPT
================================ -->
<script src="{{ '/assets/js/filter.js' | relative_url }}" defer>
</script>
