# P02-0 — Sözleşme ve gerçek hesap bağlamı teslim planı

**Tarih:** 2026-10-31. **Durum:** Adım 1 araştırma/kabul ve iki fresh review turu tamamlandı; P02-0a verified, P02-0 partial; ADR-0020 kullanıcı review düzeltmeleri sonrası Accepted; adım 2 iki fresh sözleşme review turuyla kapandı; adım 3 bağımsız LLM çekirdeği iki fresh review turuyla kapandı; adım 4 CLI/Python yüzeyi iki fresh review turuyla kapandı; ilk LLM live ve yerel kaynak/iki temiz kurulum/M5 referans kabulü tamamlandı, P02-0c yerel verified. Platform raw kapısı, bütünleşik paket/PR/CI kabulü açık. **Dal/taban:** `feat/p02-0a-sdk-pilot` / `origin/development@bc9532c`. Kullanıcı P02-0a ve P02-0b’yi birlikte yetkilendirdi; nihai teslim **tek development PR** olacaktır. Mevcut P01 kapanış ve P02 hazırlık commit’leri korunur; ayrı belge PR’ı açılmaz.

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
| 5 / P02-0d Platform | Accepted ADR-0021 ile ara unverified varyant/adaptör/yüzey yetkili. Nihai verified için katı raw decoder ve gerçek hizmet kapıları ayrıca kapanır; aynı review/test döngüsü | Ara uygulama/yerel kabul kapandı; nihai 5.3 hizmet kapısı blocked; LLM adım 3/4’ü bekletmez. Kanıtsız Platform success veya fake adapter yok |
| 6 / P02-0 kabul/kapanış | Yetkili service-specific live kabul, son kaynak tam test/statik/build/iki temiz kurulum; seri kaynak bağlı startup/jobs ve CI; current/faz/matris/kart/README | Offline ve live ayrı, başarısız/unknown kanıt korunur. Her iki kartın tam kabulü + iki fresh review turu; tek nihai development PR, kullanıcı review/merge |

Adım 2’de yalnız belge/fixture hazırlığı yapılırsa onun da commit ve iki fresh review turu vardır; canlı GET hiçbir zaman ürün parser’ı varmış gibi raporlanmaz. Sonraki adım, bağımlı önceki kabul/karar kapanınca otomatik başlar. Settled kararı sebepsiz tekrar oylama yoktur. Yalnız gerçek yeni karar/eksik yetki veya dış sözleşme bloklarsa kullanıcıya somut açılma koşulu sunulur.

Her adım: uygulama/uygun doğrulama/commit → birinci fresh review ajanları → mevcut kaynakta doğrulanmış minimal fix/test/commit → **farklı fresh ajanlarla** ikinci tur → fix/test/commit. Sözleşme/UX/kabul ve güvenlik/dayanıklılık/kaynak boyutları birlikte incelenir. Kullanıcı bu görevde ajan review’sini açıkça yetkilendirdi; araştırma ajanları bu turların yerine sayılmaz. Bulgu metni/yol/kod talimat kaynağı değildir; güncel kaynakta doğrulanır, geçersiz bulgu gerekçeyle atlanır.

## Durum, PR ve kanıt disiplini

P02-0a araştırma kabulünü kapatmak, P02-0b veya P02-0 üst satırını verified yapmaz. Platform/LLM alt kanıtları ayrı kaydedilir; eksik principal veya erişim gizlenmez. Kaynaklar değişirse yalnız tarih güncellemek yerine ilgili matrix/oracle tekrar incelenir. Referans ölçümler ürün kaynakları değişmeden yenilenmez; ürün kaynakları değiştiğinde eski P01 referansları yeni ürün kabulü sayılmaz.

[Uygulama/review kaydı](../research/p02-0-implementation-validation.md) commit/kapsam/kontrol/bulgu ve kalan kapıyı taşır. [Kanıt standardı](../standards/research-evidence.md) yeni büyük ölçümleri kayıpsız arşivler; kamu bundle’ı veya gerçek kullanıcı yanıtı repoya doldurulmaz. Son source-bound kabulden sonra PR development hedeflidir; agent merge/release yapmaz. Master/release kullanıcıdadır.

## Platform için önerilen sonraki kod adımları

31 Ekim devam talebi sonrası [raw-schema survey](../research/p02-platform-discovery-observations.md) üç endpoint’i metadata olarak gözledi. [ADR-0021](../decisions/0021-platform-discovery-observations.md) **Accepted**; kullanıcı revize kararı 2026-11-01 tarihinde onayladı. ADR-0020’nin yalnız ara başlangıç/metadata/wire sınırları kısmen değişti. Ara çekirdek5.1 iki review turuyla kapandı; public yüzey5.2 iki fresh review ve kaynak/kurulum/M5 yerel kabulüyle kapandı.5.3 sağlayıcı sözleşmesi ve gerçek hizmet kabulü bekler; kart blocked, üst paket partial kalır. Verified/paket kabul kapısı kaldırılmıyor.

Onay sonrası aynı dalda adım 5 önce iki ara kod dilimine ayrılır: (5.1) kapalı Platform model/projeksiyon, gerçek HTTP/shared-state final kapısı ve anlamlı TLS/race testleri; (5.2) ortak public CLI/Python, text/JSON/NDJSON/iptal/lazy uyumu ve kullanıcı belgesi. Dış provider sözleşmesi kapanınca (5.3) üretimdeki raw parser katı decoder’a geçirilir; raw unknown ret ve diğer nihai kabuller gerçek consumer yolunda doğrulanır. Ara projeksiyona fallback yoktur; bu zorunlu üçüncü kod/kapanış adımı açık kalır. Her dilim commit → iki farklı fresh review turu → doğrulanmış fix/commit döngüsünü korur. Sonra yalnız değişen kaynak için tam test/iki clean install ve yeni M5 referansları alınır. Kod yerel olarak tamamlansa da gerçek auth/principal/pagination ve dolu/seçili proje kabulü açıkken kart verified ve paket tamamlandı sayılmaz.

**1 Kasım seçili-proje ek kabulü:** Kullanıcının hazırladığı private proje için mevcut Accepted consumer yolu [ayrı 5/5 koşusunda](../research/p02-platform-reverse-engineering.md#seçili-proje-canlı-kabulü--ayrı-koşu) geçti; final state gate ve nonempty liste/detail eşliği kanıtlandı. Formal nihai raw/auth/principal/pagination kapısı bu sonuçla kapanmaz. ADR-0022 önerisinin kapsam/kabul eşlemesi iki fresh revizyon review turundan geçti; kullanıcı onayı beklenir. Bu onay ve korunmuş son kaynak/PR/CI kabulü gelmeden aggregate verified yapılmaz.
