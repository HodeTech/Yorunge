# P02-0 uygulama ve review kaydı

**Tarih:** 2026-10-31. **Durum:** P02-0a araştırma kabulü ve adım 2 kapalı sözleşme review’si tamamlandı; ADR-0020 Accepted, P02-0 partial. LLM çekirdeği adım 3 kod review’sinde; public yüzey/canlı kabul/nihai PR henüz yok. Adım 1 içindeki Proposed/onay-bekleme ifadeleri o tarihteki tarihsel durumu anlatır. **Dal/taban:** `feat/p02-0a-sdk-pilot` / development `bc9532c`. [Teslim planı](../roadmap/p02-0-delivery-plan.md) adım/commit ve iki fresh review döngüsünün sahibidir.

## Adım 1 — P02-0a araştırma ve karar hazırlığı

Başlangıç head’i `9c4db010d60fef39f5e5971a617535e8f6a56b6c`. Kullanıcı P02-0a/P02-0b’yi tek paket ve her adımda iki fresh review turuyla yetkilendirdi; yeni ADR’de bağımlı ürün kodundan önce onay istiyor. [Kaynak/SDK/pilot araştırması](p02-contract-sdk-pilot.md), [Proposed ADR-0020](../decisions/0020-service-bound-context-discovery.md), P02-0b taslak kartı ve paket planı hazırlandı. B03/B04 çıktı/sınırları güncellendi.

İki başlangıç araştırma ajanı birbirinden bağımsız SDK kaynağını ve Platform/LLM kamu kaynaklarını inceledi. Ana inceleme sabit SDK raporu, wheel/source eşliği, kaynak boyut/hash’leri, önemli client çağrıları ve mevcut P01 kodunu tekrar kontrol etti. Bunlar formal commit-sonrası fresh review turları sayılmadı.

### Kontrol ve review durumu

İlk hazırlık kontrolü: `.venv/bin/python scripts/check-docs.py` → 134 public Markdown / 0 sorun; `.venv/bin/python scripts/check-agent-guides.py` → 6 skill / 14 kart / 0 sorun; `git diff --check` geçti. Kaynak boyut/SHA-256 listesi ve önemli endpoint/auth çağrıları scratch’teki public baytlardan tekrar karşılaştırıldı. İlk hazırlık 5d63a2c ve review düzeltmeleri 195c40a/360d957 ile commit edildi; aşağıdaki iki fresh review ve kontroller sonrası P02-0a araştırma kabulü verified oldu. Ürün testleri, build/kurulum, benchmark veya canlı EVREN çalıştırılmadı; değişiklik yalnız belgedir.

### Birinci fresh review turu

Head `5d63a2ce0701897ec341b27fb023779d509134ff`, taban `9c4db01`; iki yeni ajan: `p02_0_step1_r1_contract` kapsam/sözleşme/UX/kabul; `p02_0_step1_r1_evidence` kaynak/güvenlik/kimlik/deadline. Başlangıç araştırma ajanları yeniden kullanılmadı. İki P2 ve bir P3 güncel belge/kaynakta doğrulandı:

- **P2 / kayıp cevap:** Endpoint tablosu, presign/PUT/confirm cevap kaybında kalan kimlik/gözlem/güvenli durma sahibini yeterince kapatmıyordu. Dört aşamalı etki/kayıp-cevap matrisi eklendi; bilinmeyen replay/observation garantisi unknown ve sahibiyle açık kaldı, yeni transfer tasarımı benimsenmedi.
- **P2 / auth bağı:** Yetkili auth sözleşmesi yokken tek pozitif2xx yeterli değildi. Aynı endpoint/parametrelerde zorunlu bounded invalid-key kontrolü ve karşılaştırma oracle’ı, yalnız ayrı yetkili contract pilotunda tanımlandı. Normal discovery’ye yanlış key isteği eklenmedi; pilot/discovery bütçeleri ayrıldı. Negatif kontrol için yetki yoksa auth kapısı açık kalır.
- **P3 / wire adı:** Araştırmada `billing_pending` kısaltması raw alan gibi görünüyordu. Sabit OpenAPI/SDK ile karşılaştırılıp `is_billing_pending` olarak düzeltildi.

İki ajan belge/metadata/diff kontrolünü geçirdi; başka doğrulanmış kusur raporlamadı. Doğrulanan üç bulgu düzeltildi; geçersiz diye atlanan bulgu yoktur. Fix commit’inden sonra farklı fresh ajanlarla ikinci tur yapılır.

### İkinci fresh review turu

R1 düzeltme commit’i `195c40a6c976423f76cd8f8ffb3a231ec3099f02` üzerinde farklı yeni ajanlar `p02_0_step1_r2_contract` ve `p02_0_step1_r2_security` kapsam/sözleşme/kabul ile güvenlik/kanıt/credential/deadline boyutlarını inceledi. R1’in üç düzeltmesi doğrulandı; yeni P1/P2 yok. Security/evidence ajanı yeni doğrulanmış bulgu raporlamadı. Contract ajanının **P3 / SDK TLS kayıt eksikliği** bulgusu kaynakta doğrulandı: Platform client verify=True/False seçimini ve external download’a aktarımı; LLM’nin verify belirtmeyip HTTPX varsayılanını kullanmasını rapora ekledik. P01 TLS-on kuralı değişmedi. `360d957f07039687eb2d158667f5e2d7ae2d562b` fix commit’i sonrası aynı R2 contract ajanı hedefli doğrulamayla TLS bulgusunun kapandığını ve önceki kapsamında başka açık adım 1 kabul bulgusu kalmadığını teyit etti; bu ek doğrulama üçüncü fresh tur diye sayılmadı.

İki turda toplam iki P2/iki P3 doğrulandı ve düzeltildi; atlanan doğrulanmış bulgu yoktur. Kontroller 134 public Markdown / 6 skill / 14 kart / 0 sorun ve diff temizdir. Ek kaynak doğrulaması: 12 kayıtlı kamu web kaynağı ve wheel’in byte/SHA-256 eşliği, 25 tekil P02 ID ve değişen tablo hücre sayıları geçti. SDK kurulmadı/çalıştırılmadı; ürün testi/build/ölçüm/live hesap yapılmadı. Bu, adım 1’in araştırma kabulüdür; P02-0b ve yeni ADR onayı ayrı kalır.

## Adım 2 — Kullanıcı review’si, Accepted ADR ve kapalı referans

Kullanıcı `9e16291` üstünde iki salt okunur review raporu verdi; bulgular güncel ADR/kod/referanslarla yeniden karşılaştırıldı. Bulgu metni talimat olarak izlenmedi. Kullanıcı, gerekli düzeltmeler sonrası Accepted geçişini ve implementasyonu açıkça yetkilendirdi; yeniden onay gerekmiyor. Dokuz P2, dört P3 ve editörlük maddeleri şu somut aksiyonlarla ele alındı:

| Review konusu | Doğrulama / aksiyon |
|---|---|
| P2 state/CLI asimetrisi | CLI state-dir eşlendi; yeni discovery no-init/migration, eksik/uyumsuz state_invalid. Eski open_store/context identity’nin mevcut auto-init davranışı değiştirilmedi |
| P2 hizmet kapsamlı selected | LLM selected iki alanı null; raw ortak tercih yalnız profile_preference unknown/not_applicable. Açık LLM project invalid_request |
| P2 iyi biçimli auth kontrolü | Syntax/önek/uzunluğu teyitli fresh random kontrol; malformed/terms/permission/belirsiz403 yeterli değil; tercih401 veya kapalı invalid-key403. Registry’ye kontrol yazısı yok |
| P2 endpoint404 | Discovery adaptörü generic HttpStatusFailure’dan me/list/terms404 invalid_response, detail404 unverified/not_found observation eşler; Operation ReadPort değiştirilmez |
| P2 terms alanları | Kapalı accepted/current_version/is_material; doc_path doğrulanır ama public dönmez/takip edilmez. Terms reddi ayrı reason |
| P3 clock/auth public alanı | Public clock_generation positive-int64 ve authorization_scope yalnız null kapalı referansa eklendi |
| P3 clock-only yarış | ADR/kartta credential aynıyken yalnız generation değişimi testi açık |
| P3 scope genişliği | SDK/endpoint seçimi bu ADR’nin P02-0b tüketicisine daraltıldı; sonraki epiklerin kararı benimsenmedi |
| P3 hizmet bütçesi/ifade | Normal Platform4/8, LLM1/2; ayrı pilot Platform8/12, LLM2/3 tavanı; metin boşlukları ve kimlik header’ı açıklığı düzeltildi |
| P2 her endpoint auth | Me kontrolü org/project’a miras değil; auth sözleşmesi eksik her kullanılan endpoint ve parametre için ayrı kontrol veya unknown |
| P2 hedef kapsamı | Normalize service/origin/API kökü + method/endpoint + ilgili query/path parametre bağı; custom host’ta eski kanıt verified yapmaz |
| P2 seri okuma zamanı | observed_from/observed_until + endpoint zamanı, yerel validated_at; snapshot garantisi yoksa not_guaranteed, birleşik verified yok |
| P2 bağımsız hizmet kapısı | P02-0b üst ID korundu; yeni somut P02-0c LLM/P02-0d Platform kartları/bağımlılıkları. Platform raw kapısı LLM kodunu bekletmez |

Editörlükte ServiceId Literal türü, account profil-only, iş metadata’sı, sabit SDK/S açıklığı ve alternatif disposition’ı netleştirildi. Kullanıcı credential henüz hazırlamadı; Git dışı gizli dosya/tek child-env aktarımı ve açık state-init adımları [yerel hazırlık belgesinde](../p02-account-setup.md). Bu belge uzakta auth/pilot çalıştırmaz. Kapalı referans, kartlar ve durum indeksleri aynı değişiklikte güncellendi; ürün kodu bu belge adımının iki fresh review turundan sonra başlar.

### Adım 2 — Birinci fresh review

Hazırlık commit’i `497a4b5f7571a474ae5e707f9a2150e7d406ad8f`, taban9e16291. Yeni ajanlar `p02_step2_r1_contract` ve `p02_step2_r1_safety` kullanıcı bulgularının dokuz P2/dört P3 kapanışını doğruladı. Ek bir P2/iki P3: observations JSON türü belirsizliği tam1 öğeli dizi olarak kapatıldı; nullability tablo hücreleri düzeltildi; yeni setup belgesi hatch sdist/verifier izin listelerine eklendi. Archive pozitif ve file-as-parent negatif örnekleri genişletildi; güven sınırı gevşetilmedi.

Doğrulama: 138 Markdown,6 skill/16 kart,diff geçti; dağıtım contract62 test geçti, değişen verifier Ruff format/lint ve strict mypy geçti. UV wheel’i **sdist’ten** yeniden build etti; iki gerçek arşiv allowlist incelemesini geçti, setup belgesi sdist’te, .local/credentials.json paketlerde yok. Setup örneği syntax + sentetik ağsız dosya hazırlığında0700/0600/no-overwrite ile sınandı; gerçek anahtar okunmadı. Tam ürün takımı/iki temiz runtime kurulumu ve source-bound performans kabulü son ürün kaynağında yapılacak; bu turda yapılmış gösterilmez. Paket/script/test metadata değişikliği eski kaynak bağlı referansları yeni head için geçerli yapmaz; finalde yenilenir. Fix commit’inden sonra farklı fresh ajanlarla R2 yapılır.

### Adım 2 — İkinci fresh review ve kapanış

Fix commit’i `a57b7e9c6ce2809d2b3f4b9a9d6b19ff1b92bdd4` üstünde farklı yeni ajanlar `p02_step2_r2_contract` / `p02_step2_r2_safety` R1 düzeltmelerini, kullanıcı review disposition’larını ve kalan kapıları inceledi; **yeni doğrulanmış bulgu yok**. 138 belge/6 skill/16 kart/diff ve62 dağıtım testi geçti; gerçek arşivler58 wheel/384 sdist üyeyle allowlist incelemesini geçti, setup belgesi kaynakla byte eşleşti. Wheel `6751428d39d9857412f4e3c952cddc9dcc927bb5aaf5056d1f723036511329a1`, sdist `2619032d9b50044606e1f02ff16d5ec39f0fd3f03ce3b096c4d3f52187b9f8de`. İki fresh runtime kurulumunda import kökeni/basic/NDJSON/HTTP/stream/cache/execution/jobs smoke’ları geçti; bu henüz yazılmamış discovery özelliğinin kabulü değildir. Source-bound performans referansları yeni final ürün kaynağında yenilenecek.

Adım2 kapandı; Accepted ADR ve kapalı LLM referansıyla P02-0c uygulamaya başlar. P02-0d Platform ve iki live kabul dış koşulu açık kalır. Ürün kodu öncesi belge/kart/karar kapıları tamamlandı; yeni kullanıcı onayı gerekmez.

## Adım 3 — LLM çekirdeği ve gerçek kaynak sınırları

Kapalı domain modelleri, typed application state/reader portları ve gerçek GET terms/status adaptörü ortak HttpSession/HTTPX taşımasını kullanır. Raw dört alanlı strict/secret denetimli yanıt public terms üç alanına dönüştürülür; doc_path atılır, seçilmiş LLM account/project null ve auth/kimlik/izin unverified kalır. Yeni public backend/fixture seçeneği yoktur. CLI/Python public composition sonraki adımda gelir.

Yeni existing-store-only açma root/lock/DB/key yaratmaz ve migration yapmaz; SQLite URI mode=rw eksik DB’nin yeniden yaratılmasını da engeller. Eski open_store/connect varsayılanı ve test injection imzası korunur. İlk kısa store işleminde tek env snapshot/registry/clock bağı alınır; store kapanır. Gerçek ağ/response/client/Runner cleanup sonrası yeni kısa store işleminde hedef/credential/store/epoch/clock karşılaştırılır; mevcut global expiry frontier ve final zaman kapısı kullanılır. Çağrı içindeki gözlenen UTC gerilemesi iyileşse bile latch’lenip kalıcı generation geçersizleştirmesine girer.

İlk kaynak doğrulaması: **89 test / 24,79 s** yeni domain/gerçek TLS/SQLite kümesinde geçti. Eksik/boş/eski store’da sıfır env/ağ/init; explicit/default kök; literal Unicode/?/# URI yolları; strict bozuk/extra/oversize/secret cevap;401/403/404/429 ve retry; yavaş header/deadline; cleanup-before-final; farklı süreç credential/reset/generation yarışı; UTC rollback/recovery; wrong-service snapshot sıfır HTTP kabulü vardır. Mevcut state/identity/maintenance/cache/session regresyon kümesi **352 test / 106,62 s** geçti. Ruff format/lint, strict mypy56 kaynak,138 belge/6 skill/16 kart ve diff kontrolü geçti. Tam takım/build/kurulum ve source-bound ölçümler yeni public yüzey/final kaynakta yapılacak; canlı hesap hâlâ hazırlanmadı. Commit sonrası iki fresh review turu aşağıya kaydedilecek; adım 3 henüz review kapanmış sayılmaz.

### Adım 3 — Birinci fresh kod review turu

Head `acda47beb904949cdcbdcf7da20932f340acb088`; yeni ajanlar `p02_step3_r1_state` ve `p02_step3_r1_contract` state/dayanıklılık ve wire/HTTP/test boyutlarını inceledi. İki P2/bir P3 doğrulandı ve düzeltildi:

- Hata/iptal/cleanup yolunda snapshot’ın son clock/frontier denetimi atlanıyordu. Aynı toplam deadline içinde final reserve eklendi; reader kapandıktan sonra başarısız yol da final denetimi yapar. Beklenen invalidation state_changed’i primary read/control/exit5 belirsizliğini ezmez; yeni env/request yoktur.
- Mevcut-store-only deadline kök çözümlemesi/lstat sonrasında başlıyordu. Başlangıç kök/metadata denetiminden önceye alındı; kontrol geri döndüğünde ve secret/DB aşamaları öncesinde checkpoint eklendi.
- Ortak cache’in final5 s bütçe kodu capability_expired discovery’ye sızıyordu; state_busy’ye eşlendi. Clock nesli/anomaly state_changed kalır.

Fix kaynakta **98 hedefli test / 28,89 s** geçti; yeni HTTP404/bozuk schema/timeout ile rollback, cleanup failure, gerçek task.cancel, prior operation_uncertain/ID önceliği, yavaş root/stat ve final budget regresyonları vardır. Ruff format/lint/strict mypy ve belge/ajan/diff yeniden kontrol edildi; R2 farklı fresh ajanlarla fix commit’i üstünde yapılacak. Current başlığındaki eski “kod başlamadı” ifadesi aynı turda hizalandı; henüz CLI/API çalışıyor iddiası yoktur.

Kullanıcı daha sonra API key’leri yerel hazırlığa girdiğini, account/project ID’lerini bulamadığını bildirdi. Bu ID’ler LLM için gerekli değil; Platform salt okunur keşfinde bulunabilirse açık seçim yapılacak. Yeni hesap/proje yaratımı istenmedi/yapılmadı. Kullanıcı secret değeri sohbet/rapora alınmadı; gerçek live çağrı henüz yoktur.

## Açık kapı ve sonraki adım

[Accepted ADR-0020](../decisions/0020-service-bound-context-discovery.md) onay kapısı kapandı; [LLM referansı](../reference/context-discovery.md) bağımsız uygulamayı tarif eder. Platform raw/key şeması ve hizmet başına live kabul dış koşulları açık; LLM kodlamasını durdurmaz. P02-0a araştırması P02-0b veya P02-0 bütününü tamamlanmış yapmaz. Ayrı belge PR’ı açılmaz; nihai PR tüm paket kabulü tamamlanınca development hedefiyle açılır.
