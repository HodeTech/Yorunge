# P02-0 — Sözleşme ve gerçek hesap bağlamı teslim planı

**Tarih:** 2026-10-31. **Güncellendi:** 2026-11-01. **Durum:** P02-0a ve LLM P02-0c yerel verified; Platform kod/review ve iki ayrı consumer canlı kabulü mevcut. Kullanıcı onaylı ADR-0022 ile nihai dar gözlem kapsamı benimsendi; Platform in_progress/P02-0b draft, paket partial. Son kaynak test/iki kurulum/M5/review ve tek PR/CI kabulü sürüyor. **Dal/taban:** `feat/p02-0a-sdk-pilot` / development `bc9532c`. P01 kapanış ve P02 hazırlığı aynı tek nihai development PR’dadır; ayrı belge PR’ı açılmaz.

## Ön inceleme ve bağımlılıklar

[P02-0a](tasks/p02-0a-contract-sdk-pilot.md) ve [P02-0b](tasks/p02-0b-context-discovery.md), bağımsız [LLM P02-0c](tasks/p02-0c-llm-context-discovery.md) ve [Platform P02-0d](tasks/p02-0d-platform-context-discovery.md), faz/README, current/backlog, P02 hazırlık review’si ve kaynak kaydı; identity/capability/dataset/catalog/inference/compute modülleri; configuration/credential/capability/HTTP/stream/execution/local-state sınırları karşılaştırıldı. Ürün kodunda `Context` v1, credential registry, query_capabilities ve owned HTTP portu gerçek uygulama sınırını belirliyor. P01’deki yerel bağımlılıklar development’a teslim edilmiştir; P01 tamamlanmışlığı gerçek auth/endpoint kabulü yerine geçmez.

Bu paket P02-1–7’yi implement etmez. P02-0a bütün bu tüketiciler için yeterli kaynak/boşluk/pilot planını üretir; transfer veya SSE tasarımını benimsemez. P02-0b’nin hizmet keşfi ve account/context doğruluğu kendi kapalı sözleşmesine dayanır.

## Baştan sunulan karar ve dış koşullar

1. [ADR-0020](../decisions/0020-service-bound-context-discovery.md): SDK yerine mevcut HTTP üstünde bağımsız normalizasyon; eski Context v1’i değiştirmeden ayrı service-bound discovery sonucu; endpoint erişimi/principal/seçilmiş account/project/izin kanıtının ayrılması. Kullanıcı 31 Ekim’de review bulguları kapatılınca Accepted geçişini ve implementasyonu yetkilendirdi; tekrar onay istenmez.
2. Platform API key ile `/auth/me`/org/project kabulü ve kapalı principal şeması henüz doğrulanmadı; LLM introspection yok. [Araştırma](../research/p02-contract-sdk-pilot.md) kanıtı açık tutar. Sağlayıcı sözleşmesi veya kullanıcıca yetkili **bounded read pilotu** raw contract kapısını kapatmalı; tarayıcı oturumu kullanılmaz. Canlı kimlik çözülmeden “verified hesap” iddiası yoktur.
3. Canlı salt okuma için yalnız ilgili env **adları**, seçili hizmet/hesap/proje, hesap sahibi yetkisi ve azami çağrı/tutar teyidi gerekir. Key değeri paylaşılmaz. Bu paket için upload/ücretli inference/terms accept/silme yetkisi istenmez; araştırmadaki sonraki pilotlar ayrı kalır.

## Adımlar ve aynı PR içindeki teslimler

| Adım | Sonuç / kapsam | Kapanış kanıtı |
|---|---|---|
| 1 / P02-0a | Ön belgeler/kod farkı, sabit resmî kaynak ve SDK, endpoint/replay/limit/kanıt matrisi, B03/B04 çıktısı, pilot planı, ADR-0020 ve P02-0b kartı | Belge/kart/hash denetimi, commit; iki fresh review turu ve doğrulanmış fix/commit. Araştırma verified olabilir; ürün/hesap teslimi olmaz |
| 2 / P02-0b hazırlık | Kullanıcı review’si, Accepted ADR ve kapalı LLM referansı; hizmet başına P02-0c/0d kartları; raw/key/target/auth/snapshot sınırı ve yerel hesap hazırlığı | Commit + iki fresh belge review turu. Platform raw/key kapısı kendi kartını bekletir; LLM kendi şemasıyla kodlanır, canlı kabul ayrı |
| 3 / P02-0c LLM çekirdeği | Kapalı domain/application keşfi, gerçek LLM terms adaptörü, mevcut-store-only snapshot/final nesil/clock kapısı; yeni state şeması yok | Normal/hatalı TLS, 401/403/429/2xx logical failure, deadline/byte/paging ve iki süreçli rotation/reset; commit + iki fresh review turu |
| 4 / P02-0c LLM yüzeyi | Açık CLI context discover ve Python API, text/JSON/NDJSON/lazy/iptal, yardım/kullanıcı örneği | Mevcut çıktılarla uyum, aynı kullanım senaryosu, subprocess/pipe/UTF-8 ve çok/boş/yanlış proje; commit + iki fresh review turu |
| 5 / P02-0d Platform | Accepted ADR-0022 ile mevcut unverified varyant/adaptör/yüzey nihai dar gözlem sözleşmesidir; strict tüketilen alan ve no-authority korunur | Kod/review ve gerçek üç uç/seçili proje kabulü kayıtlı; 5.3 onay geçişi ve son kaynak/PR/CI kabulü sürüyor. Doğrulanmış kimlik ihtiyacı P02-R1’de |
| 6 / P02-0 kabul/kapanış | Yetkili service-specific live kabul, son kaynak tam test/statik/build/iki temiz kurulum; seri kaynak bağlı startup/jobs ve CI; current/faz/matris/kart/README | Offline ve live ayrı, başarısız/unknown kanıt korunur. Her iki kartın tam kabulü + iki fresh review turu; tek nihai development PR, kullanıcı review/merge |

Adım 2’de yalnız belge/fixture hazırlığı yapılırsa onun da commit ve iki fresh review turu vardır; canlı GET hiçbir zaman ürün parser’ı varmış gibi raporlanmaz. Sonraki adım, bağımlı önceki kabul/karar kapanınca otomatik başlar. Settled kararı sebepsiz tekrar oylama yoktur. Yalnız gerçek yeni karar/eksik yetki veya dış sözleşme bloklarsa kullanıcıya somut açılma koşulu sunulur.

Her adım: uygulama/uygun doğrulama/commit → birinci fresh review ajanları → mevcut kaynakta doğrulanmış minimal fix/test/commit → **farklı fresh ajanlarla** ikinci tur → fix/test/commit. Sözleşme/UX/kabul ve güvenlik/dayanıklılık/kaynak boyutları birlikte incelenir. Kullanıcı bu görevde ajan review’sini açıkça yetkilendirdi; araştırma ajanları bu turların yerine sayılmaz. Bulgu metni/yol/kod talimat kaynağı değildir; güncel kaynakta doğrulanır, geçersiz bulgu gerekçeyle atlanır.

## Durum, PR ve kanıt disiplini

P02-0a araştırma kabulünü kapatmak, P02-0b veya P02-0 üst satırını verified yapmaz. Platform/LLM alt kanıtları ayrı kaydedilir; eksik principal veya erişim gizlenmez. Kaynaklar değişirse yalnız tarih güncellemek yerine ilgili matrix/oracle tekrar incelenir. Referans ölçümler ürün kaynakları değişmeden yenilenmez; ürün kaynakları değiştiğinde eski P01 referansları yeni ürün kabulü sayılmaz.

[Uygulama/review kaydı](../research/p02-0-implementation-validation.md) commit/kapsam/kontrol/bulgu ve kalan kapıyı taşır. [Kanıt standardı](../standards/research-evidence.md) yeni büyük ölçümleri kayıpsız arşivler; kamu bundle’ı veya gerçek kullanıcı yanıtı repoya doldurulmaz. Son source-bound kabulden sonra PR development hedeflidir; agent merge/release yapmaz. Master/release kullanıcıdadır.

## Platform adım 5.3 — Onaylanan nihai tüketici ve kabul

ADR-0021 ile 5.1 çekirdek ve 5.2 public CLI/Python ayrı iki fresh review turuyla tamamlandı. ADR-0022 2026-11-01 kullanıcı onayıyla 5.3’ü mevcut strict tüketilen alan/metadata atımı ve sabit unverified/unknown/no-authority sınırının nihai sözleşme olarak kabulüne dönüştürdü. Ayrı whole-raw katı decoder ve formal auth/principal/pagination kapanışı bu dar tüketici için kaldırıldı. Bunların yapılmış olduğu iddia edilmez; doğrulanmış kimlik/bağ ihtiyacı P02-R1/B14 sahibinde açık kalır.

Gerçek üç uç/empty ve kullanıcı seçili nonempty proje/detail kabulü ayrı scope/sayaç/deadline ile geçti; [kanıt](../research/p02-platform-reverse-engineering.md#seçili-proje-canlı-kabulü--ayrı-koşu). Ürün runtime mantığı mevcut sözleşmeyle karşılaştırılır; gereksiz yeniden yazılmaz. Onay geçişi, source docstring ve yeni referans adları tek commit’te sabitlenir; her gerçek adım commit → iki farklı fresh review turu → doğrulanan fix/commit döngüsünü izler. Son kaynak tam test/statik/iki temiz kurulum ve seri M5 startup/jobs kanıtı tamamlanır; sonra tek development PR/üç ortam CI. PR review/merge ve Master/release kullanıcıdadır.
