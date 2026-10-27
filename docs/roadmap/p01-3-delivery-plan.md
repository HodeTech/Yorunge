# P01-3 — Capability ve execution hazırlığı teslim planı

**Tarih:** 2026-10-27. **Durum:** Uygulanıyor; ADR-0013/0014 ve bağlı ScopeV2 2026-10-27 kullanıcı onayıyla Accepted. **Dal:** feat/p01-3-capability-planning. **Taban:** development@78d5d77. İlk uygulama adımı başladı; ürün kabulü henüz yoktur.


**Güncel onay:** ADR-0013/0014 ve bağlı ScopeV2, 2026-10-27 açık kullanıcı onayıyla Accepted. Aşağıdaki hazırlık/review kayıtlarındaki Proposed ve onay bekleme ifadeleri tarihseldir; uygulama kabulü ayrıca kaydedilir.

Gerçek kod/test/ölçüm, adım commit'leri ve iki review turunun tek kanonik kaydı [uygulama kabulüdür](../research/p01-3-implementation-validation.md). İlk cache adımı uygulanıyor; epik henüz kapanmadı.
## Teslim sınırı

Kullanıcı sonucu: capability bilgisinin hangi hedef/kimlik/kanıta ait ve ne kadar güncel olduğunu görmek; ayrı execution hazırlığını kaydetmek; değişmiş girdi/yetkiyle eski plan veya onayın geçerli sayılmasını engellemek. [P01-3a](tasks/p01-3a-scoped-capability-cache.md) ve [P01-3b](tasks/p01-3b-execution-plan-validity.md) tek development PR'ında teslim edilir. Paket L büyüklüğündedir; iki kart ve aşağıdaki M uygulama adımlarına ayrılır. Bunlar süre tahmini değildir.

Offline v1 Plan/capability ve seçim önceliği korunur. Uzak discovery/auth, gerçek araç/execution adaptörü, run, operation/attempt/lease/jobs, HTTP/NDJSON ve gerçek EVREN bu paketin dışında kalır; özgün P01-4/5/P02/P03 sahiplerine bağlıdır. Bunların yerine üretim fixture'ı veya sahte başarı konmaz. Kullanıcının gereksiz ertelememe tercihiyle yeni state tüketicilerinin reset/restore/recover uyumu bu pakette tamamlanır.

## Hazırlık kapısı

[Ön inceleme ve araştırma](../research/p01-3-readiness-review.md) mevcut kodu, ilgili kanonik belgeleri ve üç bağımsız audit'i kapsar. P01-2b/P01-4a [PR #6](https://github.com/HodeTech/Yorunge/pull/6) ile development'a alınmıştır; kapanış tabanı [PR #7](https://github.com/HodeTech/Yorunge/pull/7)'dir. Önkoşul teslimi mevcut; aşağıdaki kararlar 2026-10-27 kullanıcı onayıyla Accepted:

- [ADR-0013](../decisions/0013-scoped-capability-cache.md): Yeni scope/kanıt, cache/clock/TTL/kota ve açık sorgu.
- [ADR-0014](../decisions/0014-execution-plan-validity-and-approval.md): Execution/onay/yerel kayıt yönetimi ve restore/recover/preview uyumu.

Kullanıcının mevcut talebi uygulama, commit, bağımsız review ve son development PR'ını yetkilendirir. Yeni ADR'ler ve bağlı wire için açık onay alındı; ilk kartın doğrudan bağımlılıkları kanıtlı olduğundan uygulama başladı; P01-3b, P01-3a kabulü oluşmadan uygulamaya hazır gösterilmez.

## Uygulama adımları

| Adım | Sonuç / commit sınırı | Başlama kapısı | Review odağı |
|---|---|---|---|
| 1 | P01-3a bütünü: v2 tipli kayıt/producer/resolver, gerçek SQLite cache+clock migration, epoch/nesil ve kota, CLI/Python açık cached/refresh; cache-only restore/recover uyumu | İki ADR onayı, P01-2 önkoşul kanıtı | Trust/TTL/saat; concurrency/migration/bakım; public uyumluluk/performans |
| 2 | P01-3b hazırlık/validity: ayrı değişmez plan, gerçek yerel dosya bağlama, kalıcı kayıt/list/show/validate, plan tüketicisinin bakım önizleme/restore entegrasyonu | Adım 1 kabulü ve iki review turu | Girdi/TOCTOU; saved seçim/hedef/yetki; plan şeması/digest/store/epoch/clock |
| 3 | P01-3b onay/yönetim: güncel validation sonrası digest onayı, revoke/forget/kota, bütün bakım v2 ve önceki runtime intent kurtarma kabulü | Adım 2 kanıtı ve iki review turu | Onay/replay/sır; reset/restore/legacy intent; CLI/Python/hata ve FK sınırı |
| 4 | Bütünleşik teslim: uçtan uca offline/stateful/blocked akış, tam build/iki temiz kurulum, hacimli cache başlangıç ölçümü, kanonik belge/kart kapanışı ve son PR | Adım 1–3 kabulü ve her birinin iki review turu | Paket/sızıntı/kaynak; kanıt/durum/belge; gelecek operation tüketicisine devir |

İlk adımın tek kabulü fazla büyürse aynı kart içinde domain/SQLite ve public entegrasyon commit/review adımlarına ayrılır; hiçbir kabul sessizce düşürülmez. Boş port/tablo veya tüketicisiz şema sırf sırayı doldurmak için oluşturulmaz. Her schema adımı gerçek tüketicisiyle gelir; eski migration değiştirilmez.

## Her adımın döngüsü

1. Kod, anlamlı negatif/olumlu test ve ilgili kullanıcı/referans belgesini birlikte tamamla; uygun yerel kontrolleri koş ve commit et.
2. İşin boyutuna uygun yeni bağımsız ajanlarla birinci çok boyutlu review turunu yap. Bulguları mevcut kodda doğrula; geçerli olanları düzelt, test et ve commit et. Geçersiz iddiayı kısa gerekçeyle kaydet.
3. Başka yeni bağımsız ajanlarla ikinci turu yap; aynı doğrulama/düzeltme/commit döngüsünü tamamla. Çözümlenmemiş gerçek kabul/güvenlik sorunu varsa sonraki adıma geçme.
4. Test/commit/review kanıtını aynı dalın uygulama kaydına yaz; engel veya yeni kullanıcı kararı yoksa sonraki adıma otomatik geç.

Model/effort karmaşıklığa göre seçilir: domain/state/güvenlik için high effort, karmaşık recovery/çok süreçli yarışlarda ayrıca bağımsız güçlü reasoning incelemesi. Kullanıcının bu görevdeki açık talimatı review ajanlarını yetkilendirir. PR sonunda kullanıcı incelemesi beklenir; ajan bu ürün PR'ını kendiliğinden merge etmez.

## Bütünleşik kabul ve kanıt

Kartların ayrıntılı kabulü tek kaynaktır. Paket kapanışında bunların birlikte çalıştığı kanıtlanır: iki credential/hedef/kapsam izolasyonu, saat/expiry ve kaynak güveni, eski v1 byte/digest uyumu, gerçek input değişimi, plan/onay invalidation, reset/restore/legacy recovery ve son transaction'da bağ çatışması. Fixture pozitif sonucu ile üretimde blocked/unknown sınırı ayrı kaydedilir.

[CONTRIBUTING matrisine](../../CONTRIBUTING.md#doğrulama-seçimi) göre tam offline test, Ruff format/lint, strict mypy, belge/ajan denetimi, wheel/sdist iki temiz kurulum ve gerçek import kökeni; help/version p95 ≤500 ms ve kayıtlı hacimde cache/profil okuma p95 ≤200 ms gerekir. Ölçüm en az 30 ayrı süreç, ortam/CPU/disk/kurulum biçimi/veri hacmiyle kaydedilir. Son head'in `offline-core`/`branch-policy` CI'ı beklenir. Gerçek Windows, fiziksel güç kesintisi veya canlı EVREN kanıtı üretilmiş sayılmaz.

## Hazırlık teslim kaydı

Ürün commit/test/benchmark/PR kanıtı henüz yoktur. Ön inceleme raporu, Proposed ADR'ler ve draft kartlar `13f50f4` hazırlık commit'inde kaydedildi. İlk hazırlıkta belge kontrolü 102 dosyada, ajan rehberi kontrolü altı skill/yedi kartta sorunsuz ve diff boşluk kontrolü başarılıdır; runtime test/build/benchmark çalıştırılmadı.

Yeni üç ajanla ilk belge review turu tamamlandı: trust/clock (GPT-6 Astra/high), recovery/state ve scope/UX (GPT-6.1 Sol/high). Kalıcı saat geçersizleştirme mekanizmasının eksikliği ve kota dolunca ID keşif yolunun bulunmaması doğrulandı; clock generation ve bounded plan listesi `751c77c` ile eklendi. Forget'in eşzamanlı onayı silme anlamı ve hash kaynak bütçesi ayrıca açıklaştırıldı.

Başka üç yeni ajanla ikinci turda (invariants GPT-6 Astra/high; public-contract ve state-acceptance GPT-6.1 Sol/high) ilk düzeltmeler doğrulandı. İlk cache kabulünün sonraki plan/onay tüketicisini gerektirmesi giderildi; bu kabul gerçek tüketicinin P01-3b/bütünleşik adımına bağlandı. [Ayrıntılı kayıt](../research/p01-3-readiness-review.md#önerilerin-bağımsız-review-kaydı). Kararlar hâlâ Proposed, kartlar draft; ürün uygulaması yoktur.

İkinci tur düzeltmelerinden sonra `check-docs.py` 102 dosya/0 sorun, `check-agent-guides.py` altı skill/yedi kart/0 sorun ve `git diff --check` başarılıdır. Runtime/test/script/example/dependency/CI dosyaları değişmedi; runtime test/build/benchmark bu belge hazırlığında çalıştırılmadı. Sıradaki kapı kullanıcının iki ADR için açık onayıdır.

Sonraki kullanıcı review'lerinin yedi maddesi mevcut öneri/kodla doğrulandı; [bulgu/aksiyon tablosu](../research/p01-3-readiness-review.md#kullanıcı-reviewlerinin-doğrulanması) kanoniktir. Final süre kapısı, input descriptor/root/CWD bağı, tam context imzaları, discovery'siz tarihsel aday güveni ve concurrent refresh merge/overflow politikası eklendi. [CapabilityScopeV2 wire](../reference/capability-scope-v2.md) artık onay kapsamındaki kapalı şemadır. Bunlar ilk dört adımın kabulünü somutlaştırır; yeni ürün capability'si veya ADR onayı değildir. Kararların kullanıcı onayı beklenmeye devam eder.

Bu düzeltmeler `7d9df80`, ilk bağımsız review sonrası normal çelişki proof saklama düzeltmesi `a1889c9` commit'indedir. İkişer yeni ajanla iki review turu tamamlandı; ikinci turda yeni bulgu yok. Son belge kontrolü 103 dosya/0 sorun, ajan kontrolü altı skill/yedi kart/0 sorun ve diff whitespace başarılıdır. Kod/test/build/performance kabulü henüz yapılmadı; ADR-0013/0014 ve bağlı scope wire Proposed, iki kart draft kalır.
