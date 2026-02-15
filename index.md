---
layout: default
title: TOP
---

<section class="hero">
  <div class="container">
    <h2>MissConnect</h2>
    <p>
      Refined. Precise. Professional.<br>
      ミスコン出身者やインフルエンサーをご紹介します
    </p>
    <a href="{{ '/talents/' | relative_url }}" class="btn-primary">
      VIEW TALENTS
    </a>
  </div>
</section>

<section class="agency-statement" style="padding: 120px 0; text-align:center;">
  <div class="container">
    <h3 style="font-size: 24px; letter-spacing: 0.15em; margin-bottom: 30px;">
      ABOUT US
    </h3>
    <p style="max-width: 700px; margin: 0 auto; color: #9a9a9a;">
      案件に返信があったインフルエンサーへの対応、日程調整、および実際の撮影実施までのサポートを行います
    </p>
  </div>
</section>

<section class="featured-talents" style="padding-bottom: 120px;">
  <div class="container">
    <h3 style="text-align:center; font-size: 24px; letter-spacing: 0.15em; margin-bottom: 60px;">
      FEATURED TALENTS
    </h3>

    <div class="talent-grid">
      {% for talent in site.talents limit:8 %}
      <div class="talent-card">
        <a href="{{ talent.url | relative_url }}">
          <div class="image-wrapper">
            {% if talent.images %}
              <img src="{{ talent.images[0] | relative_url }}" alt="{{ talent.name }}">
            {% else %}
              <img src="{{ '/assets/images/talents/sample.png' | relative_url }}" alt="{{ talent.name }}">
            {% endif %}
          </div>
          <div class="talent-info">
            <h3>{{ talent.name }}</h3>
            <p>{{ talent.kana }}</p>
          </div>
        </a>
      </div>
      {% endfor %}
    </div>

    <div style="text-align:center; margin-top:60px;">
      <a href="{{ '/talents/' | relative_url }}" class="btn-primary">
        ALL TALENTS
      </a>
    </div>
  </div>
</section>