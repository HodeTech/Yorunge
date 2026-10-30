---
id: P02-0c
phase: P02
status: in_progress
size: M
depends_on: [P02-0a, P01-2b, P01-3a, P01-5a, P01-5b]
capabilities: [C01, C02, C13]
---
# P02-0c — Bağımsız LLM context ve terms keşfi

**Tarih:** 2026-10-31. **Durum:** İki fresh sözleşme review turu kapandı; LLM çekirdeği iki fresh review turuyla kapandı; public CLI/Python yüzeyi review/kabulünde. [P02-0b](p02-0b-context-discovery.md) üst tesliminin LLM koludur; ek PR açılmaz.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı seçili LLM anahtarı/hedefine açık terms sorgusu yapar; şart durumu ile kimlik/auth/izin eksikliğini ayrı görür. Ortak profilin Platform account/project tercihleri LLM seçimi olmaz. P01 yerel credential ve taşıma sağlar; bu çalışma dalında gerçek endpoint/adaptör ve CLI/API eklendi. Nihai kaynak ve canlı kabul henüz kapanmadı.

## Giren ve girmeyen kapsam

GET terms/status, kapalı ContextDiscovery LLM varyantı, explicit-existing-store/credential-clock snapshot/final kapısı, CLI/Python ve kaynak/negatif testleri girer. Profil ortak tercihleri yalnız scope=unknown/not_applicable metadata’sı olur; selected=null, provider kimliği not_exposed, authorization_scope=null kalır. İlk sürüm auth’u her hedefte unknown gösterir; provider kimliği veya write izni üretmez.

Platform identity/org/project, browser JWT, model/kota taraması, terms accept, ücretli çıkarım, yeni DB/cache veya public kanıt/pilot flag’i yoktur. Custom hedefte2xx auth verified sayılmaz. Platform kartının kapalı olması bu LLM kodlamasını bekletmez; gerçek LLM pilot kabulü ayrıca gereklidir.

## Bağımlılıklar ve kararlar

P01 bağımlılıkları development’da ve P02-0a araştırması [9e16291](https://github.com/HodeTech/Yorunge/commit/9e16291c6468d1d1f4fe47fbe891eb943107067b) üzerinde verified. Kullanıcı 31 Ekim’de review düzeltmeleri sonrası ADR-0020 kabulünü ve implementasyonu yetkilendirdi. [Accepted karar](../../decisions/0020-service-bound-context-discovery.md), [kapalı referans](../../reference/context-discovery.md) ve iki fresh belge review turu kod başlamadan kapanır. Kullanıcı live credential hazırlığını yaptı; account/project ID’leri LLM için gerekli değil. bu kabul dış koşulu offline uygulamanın önkoşulu değildir.

## Sözleşme ve uygulama sınırı

Domain kapalı model ve değişmezler; application tek kullanım senaryosu ve typed snapshot/observe/final portları; adaptör gerçek HTTP/SQLite; api.py lazy composition ve CLI parse/render sınırıdır. Referans eski v1 Context/config/Plan/Result’u korur. Raw terms dört alanlı strict modeldir; doc_path doğrulanır ama public’e girmez/takip edilmez. SQLite şeması değişmez; yeni discovery no-init reader eski open_store davranışını değiştirmez.

## Kabul

1. Default/açık state kökü ve eksik/uyumsuz store senaryosu: eksikte state_invalid/2, sıfır env/ağ/yeni dosya; aktif loop/thread/PID/reentrancy ve açık LLM project I/O öncesi invalid_request.
2. Gerçek TLS üzerinden tek mantıksal GET, tek service/env snapshot ve Bearer header; timeout/read-only retry≤2, response/total≤1 MiB/30 s; 404→invalid_response,401/403/429 ve yanlış schema/2xx logical failure/duplicate/nonfinite/secret kontrollü hata. Session/body kaynakları kapanır.
3. terms true/false, strict bool/int64/doc_path sınırları; alan/extra/wrongtype oracle’ları; kısa secret yanlış pozitifliği yok, reflected uzun canary veya tam eşleşen dinamik değer reddedilir.
4. LLM selected iki alanı null; profile_preference doluysa scope unknown, boşsa not_applicable; provider not_exposed/auth unknown/izin null; terms_not_accepted, auth unknown ve kimlik nedeni ayrı. Farklı host/kök/parametrede kanıtsız verified üretilemez.
5. Ağ sırasında iki süreçle credential revision, epoch reset veya yalnız clock generation değişir; final state_changed, env bir kez, eski sonuç publish yok. Ağ boyunca store lock’u tutulmaz; cleanup sonrası global expiry/final deadline kapısı korunur.
6. CLI/API aynı typed core; eski Context/config/Plan eşliği; UTF-8 JSON/NDJSON, non-TTY promptsuz, SIGINT/BrokenPipe ve local-only lazy import. İki hizmetli sentetik profilde≤3 komutla doğru hizmet ve kimlik/terms sınırını bulma; yanlış hedefe0 istek.
7. Hedefli + tam test/statik, wheel/sdist kurulum ve yeni kaynak bağlı startup/jobs; her kod adımı commit+iki fresh review, doğrulanmış fix. Gerçek LLM live kabulü ayrı scope/key hazırlığıyla kaydedilmeden kart verified olmaz; Platform beklenmez.

## Doğrulama

[CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi) runtime/başlangıç matrisi: meaningful unit/contract, gerçek TLS, subprocess ve çok süreçli SQLite; Ruff/strict mypy/docs/agent/diff; build/iki temiz kurulum ve seri kaynak bağlı ölçümler. CI offline/sentetik; yetkili live pilot [hazırlık yönergesine](../../p02-account-setup.md) bağlıdır.

## Teslim kaydı

Çalışma dalında çekirdek ve public yüzey var; nihai kaynak/kurulum/performans ve canlı kabul tamamlanmadığından kart verified değil. Kullanıcı review düzeltmeleri, kapalı belge review’si, LLM uygulama/test/review ve live kabul sonuçları paket kaydında işlenecek. Yeni alt ID mevcut P02-0b kapsamını bölüyor; kapsam azaltmıyor.
