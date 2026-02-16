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

    <div class="talent-grid" style="
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); /* 自動で列数調整 */
        gap: 20px;
        justify-items: center;
    ">
      {% for talent in site.talents limit:15 %}
      <div class="talent-card" style="width:160px; text-align:center;">
        <a href="{{ talent.url | relative_url }}">
          <div class="image-wrapper" style="width:160px; height:200px; overflow:hidden; border-radius:8px;">
            {% if talent.images %}
              <img src="{{ talent.images[0] | relative_url }}" alt="{{ talent.name }}" style="width:100%; height:100%; object-fit:cover;">
            {% else %}
              <img src="{{ '/assets/images/talents/sample.png' | relative_url }}" alt="{{ talent.name }}" style="width:100%; height:100%; object-fit:cover;">
            {% endif %}
          </div>
          <div class="talent-info" style="margin-top:10px;">
            <h3 style="font-size:16px; margin-bottom:4px;">{{ talent.name }}</h3>
            <p style="font-size:12px; color:#aaa;">{{ talent.kana }}</p>
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

<!-- レスポンシブ調整 -->
<style>
  .talent-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 20px;
    justify-items: center;
  }

  .talent-card {
    width: 160px;
    text-align: center;
    flex: 0 0 auto;
  }

  .talent-card .image-wrapper {
    width: 100%;
    height: 200px;
    overflow: hidden;
    border-radius: 8px;
  }

  .talent-card .image-wrapper img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  /* optional: 小さい画面で文字サイズ調整 */
  @media screen and (max-width: 500px) {
    .talent-card .talent-info h3 {
      font-size: 14px;
    }
    .talent-card .talent-info p {
      font-size: 11px;
    }
  }
</style>
