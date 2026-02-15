---
layout: default
title: TALENTS
---

<section class="talents-page" style="padding: 60px 0;">
  <div class="container">
    <h1 style="text-align: center; font-size: 32px; letter-spacing: 0.15em; margin-bottom: 60px;">
      ALL TALENTS
    </h1>

    <div class="talent-grid">
      {% for t in site.talents %}
      <div class="talent-card">
        <a href="{{ t.url | relative_url }}">
          <div class="image-wrapper">
            {% if t.images and t.images.size > 0 %}
              <img src="{{ t.images[0] | relative_url }}" alt="{{ t.name }}">
            {% else %}
              <img src="{{ '/assets/images/talents/sample.png' | relative_url }}" alt="{{ t.name }}">
            {% endif %}
          </div>

          <div class="talent-info">
            <h3>{{ t.name }}</h3>
            {% if t.kana %}
              <p class="kana">{{ t.kana }}</p>
            {% endif %}

            <ul class="basic-info">
              {% if t.height %}
                <li>身長：{{ t.height }}cm</li>
              {% endif %}
              {% if t.gender %}
                <li>性別：{{ t.gender }}</li>
              {% endif %}
              {% if t.university %}
                <li>大学：{{ t.university }}</li>
              {% endif %}
            </ul>

            {% if t.career %}
              <div class="career">
                {% if t.career.first %}
                  {% for c in t.career limit:2 %}
                    <p>{{ c }}</p>
                  {% endfor %}
                {% else %}
                  <p>{{ t.career }}</p>
                {% endif %}
              </div>
            {% endif %}

            {% if t.tags and t.tags.size > 0 %}
              <div class="tags">
                {% for tag in t.tags %}
                  <span class="tag">#{{ tag }}</span>
                {% endfor %}
              </div>
            {% endif %}
          </div>
        </a>
      </div>
      {% endfor %}
    </div>
  </div>
</section>