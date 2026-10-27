# Mevcut durum ve sıradaki iş

**Güncellendi:** 2026-10-27.

## Bugün

- Devirdeki Git durumu doğrulandı: `Master`, temiz çalışma ağacı ve `6ec4b16` belge temeli commit'i mevcuttu. İlk uygulama `feat/offline-core` dalında `bb67b3a` ile kaydedildi.
- Kullanıcı onayıyla `development`, Master belge temelinden oluşturuldu ve varsayılan dal yapıldı. [PR #1](https://github.com/HodeTech/Yorunge/pull/1) merge commit ile development'a alındı. Koruma ve CI doğrulaması [canlı kayıtta](../research/branch-workflow-validation.md); [kanonik politika](../standards/git-release.md). `Master` birleştirmesi kullanıcıda kalır.
- P00 tamamlandı. İlk çalışan dilim: Python paketi/konsol girişi, yerel TOML context, dar YAML reçetesi, dört durumlu capability görünümü, araç seçimi ve digest'li çevrimdışı plan. CLI/Python API ortak kullanım senaryolarına bağlı.
- Plan yalnız şema/seçim düzeyinde doğrulanır; `draft`, `executable=false`, `inputs_verified=false`. Adaptör, uzak yetki, veri/model içeriği ve yürütme desteği iddia edilmez. Sahte eğitim başarısı üretilmez.
- P01-1 paket/CLI/şema/build kısmı tamamlandı; HTTP seçimi kapsam gereği P01-5'e bırakıldı. P01-2/P01-3'ün dar yerel alt kümeleri ve P01-6 kontrol altyapısı eklendi. P01 bütünü tamamlanmadı.
- Yerel test, tip/lint/format, dağıtım/temiz kurulum ve başlangıç kanıtı [kabul kaydında](../research/p01-core-validation.md). İlk PR'da 100 test ve bütün CI kontrolleri Ubuntu/Python 3.11'de geçti. Metadata kontrolü PR #2'de doğrulandı; iki dalda `offline-core` ve `branch-policy` zorunlu. Yayımlanmış paket yok.
- Genel belge ve paket girdileri izin listeleriyle sınırlandırıldı; yerel analiz arşivi üretim girdisi değildir. Site/doküman yayın sistemi henüz yoktur.
- Aktif ürün kodlaması öncesi roadmap ve ajan hazırlığı gözden geçirildi; [bulgu ve karar kaydı](../research/roadmap-readiness-review.md). P01 bağımlılık sırası ve uzak fazların paket sınırı netleştirildi. Bu hazırlık yeni ürün capability'si uygulamaz.
- P01-1 kapanış düzeltmeleri ve bağımsız review turları tamamlandı; [P01-1a teslim kaydı](tasks/p01-1a-core-acceptance-hardening.md). Kullanıcı [PR #4](https://github.com/HodeTech/Yorunge/pull/4)'ü `3d3c86b` merge commit'iyle development'a aldı; [merge sonrası CI](https://github.com/HodeTech/Yorunge/actions/runs/40489316036) başarılı. Kapanış belgeleri [PR #5](https://github.com/HodeTech/Yorunge/pull/5) ile `83bcd83` tabanına alındı. P01-1 kapsamında açık iş kalmadı; P01 bütünü devam ediyor.

## Sıradaki somut iş

**Aktif hazırlık [P01-2 tek PR paketidir](p01-2-delivery-plan.md); dal `feat/p01-2-identity-context`, taban `development@83bcd83`.** [B02/B13 araştırmasına](../research/p01-2-state-identity-decision-review.md) bağlı ADR-0011/0012 ve binding v1, 2026-10-27 kullanıcı onayıyla benimsendi. Karar kapısı kapandı; ürün uygulaması henüz başlamadı.

Onay öncesi iki incelemenin [doğrulama/düzeltme kaydı](../research/p01-2-state-identity-decision-review.md#onay-öncesi-review-bulgularının-doğrulanması) rapordadır. Reset/restore ayrımı, kalıcı no-clobber backup, migration değişmezleri ve [ortak binding v1](../reference/credential-binding-v1.md) Accepted tasarıma dahildir. Alt iş durumları uygulama/bağımlılık kanıtı olmadan ilerletilmedi.

Sıradaki uygulama [P01-2a](tasks/p01-2a-secret-resolution.md); sonra [P01-4a](tasks/p01-4a-state-foundation.md) → [P01-2b](tasks/p01-2b-credential-identity.md) → [P01-2c](tasks/p01-2c-local-context-management.md). Ardından P01-3 → P01-4 → P01-5 → P01-6 ayrı epik PR'ları gelir. Alt kartların güncel hazırlık/teslim durumu metadata'sındadır; aynı PR'da alt iş commit/test/review birimidir. [Kesin sıra](phase-01-core.md), [ajan rehberi](../../.agents/README.md).

Paralel ürün araştırması P02 veri/çıkarım görevlerinin güncel EVREN sözleşmesini doğrular. Gerçek ForgeLM/muadil adaptörleri P03'tedir; plan seçim desteği adaptör desteği değildir.

## Çözülmemiş dış sorular

EVREN workspace genel kullanıcı erişimi, haricî paket/araç kurulumu, kalıcı artefakt, managed LLM eğitim API'si ve kullanıcı LLM serving sözleşmesi. Bunlar ilgili özelliklerin durumunu sınırlar. [Araştırma soruları](../research/validation-questions.md), [backlog](backlog.md).
