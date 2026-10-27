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
- Kullanıcının P01-1 kapanış talebi için belgeler ve mevcut çekirdek yeniden incelendi. Parser/şema hata sınırı ve dağıtım denetimi bulguları [P01-1a kartında](tasks/p01-1a-core-acceptance-hardening.md) iki adım olarak somutlaştırıldı; kullanıcı kartı onayladı ve mevcut çekirdeğin kapanış düzeltmeleri başladı. Bu iş tamamlandıktan sonraki yeni özellik P01-2a olarak kalır.

## Sıradaki somut iş

**Sıradaki iş [P01-2a — env secret çözümleme](tasks/p01-2a-secret-resolution.md); güncel hazırlık/teslim durumu kart metadata'sındadır.** Hedefi yalnız açık çağrıda doğru hizmetin env referansını çözmek; yerel komutlarda sır okumamaktır. HTTP, keychain, DB, credential nesli veya execution bu karta girmez.

Sonra B02/B13 kararları → P01-4a kalıcılık temeli → P01-2b credential kimliği/nesli → P01-3a/b capability ve execution geçerliliği → P01-4b operation/lease gelir. P01-5a loopback taşıma deneyi P01-2a sonrası bağımsız yürüyebilir; bütün hattı tamamlamak P01-5b/P01-6b kabulüdür. [Kesin sıra ve durumlar](phase-01-core.md), [ajan çalışma rehberi](../../.agents/README.md).

Paralel ürün araştırması P02 veri/çıkarım görevlerinin güncel EVREN sözleşmesini doğrular. Gerçek ForgeLM/muadil adaptörleri P03'tedir; plan seçim desteği adaptör desteği değildir.

## Çözülmemiş dış sorular

EVREN workspace genel kullanıcı erişimi, haricî paket/araç kurulumu, kalıcı artefakt, managed LLM eğitim API'si ve kullanıcı LLM serving sözleşmesi. Bunlar ilgili özelliklerin durumunu sınırlar. [Araştırma soruları](../research/validation-questions.md), [backlog](backlog.md).
