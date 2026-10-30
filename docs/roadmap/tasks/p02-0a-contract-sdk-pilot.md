---
id: P02-0a
phase: P02
status: verified
size: M
depends_on: [P01-2b, P01-3a, P01-5a, P01-5b]
capabilities: [C01, C02, C03, C05, C06, C07, C11]
---
# P02-0a — Güncel sözleşme, SDK sınırı ve pilot planı

**Tarih:** 2026-10-31. **Durum:** Araştırma kabulü ve iki fresh review turu tamamlandı; verified yalnız bu araştırma kartına aittir. ADR-0020 Proposed; endpoint uygulaması ve canlı hesap pilotu yapılmadı. [P02](../phase-02-data-and-inference.md) başlangıç kartıdır. [Hazırlık review’sindeki](../../research/p02-readiness-review.md) sınırlı kaynak kontrolü bu kartın tamamlanması değildir.

## Kullanıcı sonucu ve mevcut eksik

Sonraki geliştirici hangi EVREN hizmetinde hangi çağrıyı, kimlik/limit/etki ve hata kurallarıyla uygulayacağını kanıt üzerinden seçebilir. Başlangıç kaynakları 26 Ekim’e aittir; güncel LLM şeması değişmiştir. P01 ortak taşıma sağlar; gerçek endpoint, signed URL/upload, SSE veya SDK uyumu sağlamaz. Bu farklar kod başlamadan görünür bir karar/araştırma çıktısına dönüşür.

## Giren ve girmeyen kapsam

P02’nin hesap keşfi, private normal-dosya aktarımı, veri/model kataloğu, native metin/stream/embedding/rerank/görsel çıkarım ve GPU/kota **okuma** yüzeylerinin resmî kaynak envanteri girer. Ayrıntılı contract matrisi ilk tüketicilerin gerçekten kullanacağı endpoint’lere daraltılır; bütün platformu tersine mühendislikle yeniden belgelemek hedef değildir. Kamuya açık şema/belge ve sabit sürüm SDK kaynağı okunabilir; sır veya kullanıcı hesabı gerekmez.

SDK kullanımının uygun olduğu/olmadığı endpoint’ler, P01 port farkları, gerekli Proposed ADR’ler ve küçük pilot planı çıktı olur. SDK kurulumu/core bağımlılığı, ürün kodu/test iskeleti, gerçek anahtarla auth/hesap sorgusu, ücretli çıkarım, veri yükleme, şart kabulü ve temizleme/silme bu kartta yapılmaz. P03 yönetilen eğitim durumları B04’ün ayrı kısmı olarak korunur.

## Bağımlılıklar ve kararlar

P01-2b kimlik [PR #6](https://github.com/HodeTech/Yorunge/pull/6), P01-3a scope/cache [PR #8](https://github.com/HodeTech/Yorunge/pull/8), P01-5a/b taşıma/stream [PR #11](https://github.com/HodeTech/Yorunge/pull/11) ile development’a teslim edildi. [P01 son merge/kabul kaydı](../../research/p01-remaining-implementation-validation.md#development-merge-kapanışı) ve mevcut kod bağımlılık kanıtıdır.

[ADR-0017](../../decisions/0017-bounded-http-transport.md) SDK core yasağı, tek retry sahibi, hedef/secret ve deadline; [ADR-0018](../../decisions/0018-stream-results-and-cancellation.md) terminal/iptal; [ADR-0016](../../decisions/0016-operation-admission-and-ownership.md) kalıcı dispatch latch kuralları korunur. [B03/B04](../backlog.md) bu araştırmanın çıktılarıdır; kapanmaları araştırmanın önkoşulu değildir. Yeni güven sınırı/sürüm/bütçe kararı gerekiyorsa Proposed ADR yazılır ve kullanıcı onayına sunulur; onay gelmeden bağımlı kod başlamaz. Araştırma çıktısının teslimi tüm ADR’lerin Accepted olmasına bağlı değildir.

## Sözleşme ve uygulama sınırı

Kanonik araştırma sonucu [P02-0a raporudur](../../research/p02-contract-sdk-pilot.md); commit sonrası review/kabul [P02-0 kaydında](../../research/p02-0-implementation-validation.md) tutulur. Kaynak URL/tarih/sürüm/hash ve kapsam [evidence register](../../research/evidence-register.md) üzerinden keşfedilir. Faz/current kabul matrisini kopyalamaz. Kabul edilen yeni wire/CLI/API biçimleri uygulamadan önce kendi `reference` belgesine bağlanır; araştırma bir public şema ilanı değildir.

Kimlik modülü hesap/context, dataset modülü aktarım, katalog modülü sabit model kimliği, inference modülü görev yanıtı, compute modülü kota kaynağını sahiplenir. Somut HTTPX/SDK tipi domain veya public Python API’ye taşınmaz. Yeni state tüketicisi V2 migration/backup/reset/kapasite değerlendirmesiyle gelir; bu kart DDL uygulamaz.

## Kabul

1. Resmî Platform/LLM/SDK kaynaklarının erişim tarihi, sürümü veya içerik SHA-256’sı, kanıt türü ve erişilemeyen kısımları kayıtlıdır. SPA HTML’i tam kullanım kılavuzu sayılmaz; yayımlanmış istemci, SDK iddiası ve canlı hesap sonucu birbirinin yerine geçmez. Eski snapshot sessizce güncel diye sunulmaz.
2. Seçilen endpoint matrisi hizmet/origin/API kökü, method/path, auth kaynağı/header, hesap/org/proje ve permission kapsamı, pagination, request/response/envelope, 2xx mantıksal hata, limit, request kimliği, idempotency/replay ve gözlem/uzlaştırma imkânını gösterir. Bilgi yoksa `unknown` ve açılma ölçütü yazılır; 404/boş liste genel destek kararı olmaz. OpenAPI’de bir yolun görünmesi o hesabın erişim kanıtı değildir.
3. Create/presign/PUT/confirm için etki ve kayıp cevap matrisi; signed URL’nin host/port/path/query/expiry/credential politikası; stream request gereği; Range/ETag/checksum ve version/freeze anlamı ayrıdır. P01 tek dispatch ile çok aşamalı transfer arasındaki fark, hangi karardan sonra hangi alt kartın hazır olacağıyla açıklanır. Sağlayıcı “idempotent” diyorsa kapsam/süre/payload anahtarı kanıtlanır; otomatik retry politikası kendiliğinden değişmez.
4. Sabit SDK sürümü ve dağıtım hash’i üzerinden ilgili public yüzey/dependency/lisans, env/auth/cookie/redirect/TLS, timeout/total, retry/idempotency, raw boyut/JSON/SSE/cleanup/cancellation davranışı incelenir. Her endpoint için doğrudan ortak taşıma, yalnız codec/normalizasyon kullanımı veya uygun SDK adaptörü önerisi ve kanıt boşluğu raporlanır; SDK “resmî” diye doğrulanmış sayılmaz. Ağır/ikinci istemci bağımlılığı ve yan etki retry’si ADR-0017’ye aykırı biçimde eklenmez.
5. Metin/SSE/embedding/rerank/görsel için minimum alan/terminal/usage/model referansı, bilinmeyen görev ve hata/402/403/429 davranışı kaydedilir. LLM ile Platform’ın birbirinden bağımsız ilerleyebilen alt kabulleri gösterilir. Model/revision değişmezliği yoksa sahte pin veya genel erişim iddiası kurulmaz.
6. Önerilen pilot tablosu her görev için hesap/proje sahibi, gerekli yetki, sentetik veri/format, en fazla istek/token/byte ve tutar, toplam/istek süresi, beklenen kanıt, abort koşulu, kalan private kaynak ve temizleme sorumlusunu içerir. Bilinmeyen fiyat/erişim sayıyla uydurulmaz; canlı pilot onayı öncesi nasıl çözüleceği yazılır. Token anahtar değeri, signed URL veya özel veri rapora girmez. Bu plan pilotun icrası değildir.
7. B03 ve B04’ün P02 kısmı, açık karar/ADR listesi ve sonraki P02-0b kartı için giren/girmeyen kapsam, bağımlılık ve ölçülebilir kabul taslağı güncellenir. Araştırma teslimi yetkisiz hesap veya kapalı endpoint yüzünden sahte başarıya dönmez; çözülmeyen koşullar downstream kartı draft/blocked bırakır. Rapor ve öneriler kendi içinde tutarlıysa araştırma kartı teslim edilebilir; native destek/pilot geçmiş sayılmaz.

## Doğrulama

[Belge değişikliği matrisi](../../../CONTRIBUTING.md#doğrulama-seçimi): link/anchor/H1/fence, agent metadata/bağımlılık ve diff kontrolleri. SDK kodu yalnız okunur; incelenen sürüm/path/satır veya dağıtım üyesi kaydedilir. Şema/fixture varsa bağımsız sabit örnek ve kaynağı ayrılır; büyük ham veri için [kanıt standardı](../../standards/research-evidence.md) kullanılır. Canlı hesabın veya yeni ürün testlerinin çalıştırılmadığı açıkça yazılır. Doğrulama reçetesi araştırmayı başlatma veya pilot icra yetkisi üretmez.

## Teslim kaydı

- PR/commit: [Araştırma/karar hazırlığı 5d63a2c](https://github.com/HodeTech/Yorunge/commit/5d63a2ce0701897ec341b27fb023779d509134ff), [R1 düzeltmeleri 195c40a](https://github.com/HodeTech/Yorunge/commit/195c40a6c976423f76cd8f8ffb3a231ec3099f02), [R2 TLS kanıtı 360d957](https://github.com/HodeTech/Yorunge/commit/360d957f07039687eb2d158667f5e2d7ae2d562b). Nihai PR bütün P02-0 sonunda açılacak; ayrı belge PR’ı yoktur.
- Sonuç: [Araştırma raporu](../../research/p02-contract-sdk-pilot.md) yedi kabul maddesinin kaynak/endpoint/SDK/unknown/pilot planı çıktılarını karşılar; [iki fresh review ve doğrulanan iki P2/iki P3 düzeltmesi](../../research/p02-0-implementation-validation.md) tamamlandı. 134 public Markdown, 6 skill/14 kart ve diff kontrolü geçti; 12 public kaynak/wheel boyut/hash, 25 tekil P02 ID ve tablo yapısı doğrulandı.
- Kalan sınır: ADR-0020 Proposed; [P02-0b](p02-0b-context-discovery.md) raw/API-key sözleşme ve canlı hesap kabulü draft. Araştırma unknown’ları ve sonraki transfer/SSE/limit kararları sahipleriyle raporda açıktır; ürün, pilot, SDK kurulumu veya faz kapanışı iddia edilmez. Mevcut dal önceki P01 kapanış ve P02 hazırlığını da nihai PR’a taşır.
