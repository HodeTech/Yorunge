# P02-0 uygulama ve review kaydı

**Tarih:** 2026-10-31. **Durum:** P02-0a araştırma kabulü ve adım 2 kapalı sözleşme review’si tamamlandı; ADR-0020 Accepted, P02-0 partial. P02-0c LLM çekirdeği/public yüzeyi, ikişer fresh kod review turu, ilk live terms ve yerel kaynak/kurulum/ölçüm kabulü tamamlandı; yerel verified. Platform raw sözleşmesi açık, P02-0d/P02-0b ve bütün paket tamamlanmadı; nihai PR/CI henüz yok. Önceki adımlardaki Proposed/onay-bekleme, kod/yüzey/canlı kabul/ölçüm yapılmadığı ifadeleri o aşamanın tarihsel durumudur; güncel sınır aşağıdaki yerel kapanıştır. **Dal/taban:** `feat/p02-0a-sdk-pilot` / development `bc9532c`. [Teslim planı](../roadmap/p02-0-delivery-plan.md) adım/commit ve iki fresh review döngüsünün sahibidir.

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

Kullanıcı daha sonra API key’leri yerel hazırlığa girdiğini, account/project ID’lerini bulamadığını bildirdi. Bu ID’ler LLM için gerekli değil; Platform salt okunur keşfinde bulunabilirse açık seçim yapılacak. Yeni hesap/proje yaratımı istenmedi/yapılmadı. Hazırlık config/credential/scope dosyalarının yalnız varlık/0600/sahip metadata’sı kontrol edildi; izole state henüz yoktu. Kullanıcı secret değeri sohbet/rapora alınmadı; gerçek live çağrı henüz yoktur.

### Adım 3 — İkinci fresh kod review turu ve kapanış

Head `e4a97b96982fb813e39c55f539dc89ef439ef8d2`; farklı yeni ajanlar `p02_step3_r2_state` ve `p02_step3_r2_contract` R1 düzeltmelerini state/clock/dayanıklılık ve wire/HTTP/kaynak/test boyutlarında inceledi. **Yeni doğrulanmış bulgu yok.** İki ajan bağımsız98 test koşusunu29,46/30,00 s ile geçirdi; Ruff/strict mypy56 kaynak,138 belge/6 skill/16 kart/diff geçti. No-init, mode=rw, hedef/credential/epoch/generation, kilit bırakma ve hata/iptal rezervi tutarlı bulundu. Kod adım 3 kapandı; adım 4 public CLI/Python aynı core’a bağlanır. Canlı kabul ve nihai kaynak/kurulum/performans/PR ayrı kalır.

## Adım 4 — Public LLM CLI/Python yüzeyi

`api.discover_context` ve `context discover --service evren-llm` aynı çekirdeği kullanır; public fixture/CA/backend seçeneği yoktur. Request/service/path/project ve owned session kapıları I/O öncesindedir. Platform raw kapısı açıkken unsupported_combination verir. Text terms/auth/kimlik sınırını açıklar; JSON/NDJSON Result v1 ve context_not_verified uyarısını korur. Ortak seçeneklerin önce/sonra biçimi ve discovery singleton tekrarı denetlenir; eski offline/local komutlar discovery modelini import etmez.

Gerçek TLS/private test composition ve gerçek CLI child process ile API eşliği, yalnız LLM credential’ı, varsayılan/açık/eksik store, yanlış hizmet/proje/tekrar, ASCII locale’de UTF-8, safe401/403/404, env’nin ağ başladıktan sonra tekrar okunmaması, SIGINT ve kapalı pipe doğrulandı. Store önceden açık state init ile hazırlandı; keşif bootstrap yapmaz. **292 test / 20,47 s** public discovery + mevcut CLI/NDJSON/lazy/core-boundary kümesinde geçti. Ruff format/lint, strict mypy56 kaynak,138 belge/6 skill/16 kart ve diff geçti. README/CLI/reference/module/changelog/current çalışma dalındaki gerçek alt kümeye hizalandı; canlı/nihai kaynak kabulü henüz yok. Commit sonrası iki fresh kod review turu yapılacak.

### Adım 4 — Birinci fresh review turu

Head `3555fbb`; yeni ajanlar p02_step4_r1_surface / p02_step4_r1_safety public sözleşme/uyumluluk ve güvenlik/kaynak/hata yüzeyini bağımsız inceledi. Ürün kodunda doğrulanmış kusur yok. Tek P3: C02 capability matrisinin “uzak keşif yok” ifadesi gerçek LLM terms alt kümesini geriden izliyordu; çalışma dalı/review/kabul ve açık auth/kimlik/Platform sınırıyla hizalandı. C01 uzak kimlik yok ifadesi doğru kaldı. İki ajan sırasıyla77 test/18,72 s ve53 test/16,23 s geçirdi; seçenek konumu deneyleri ve statik/belge/ajan/diff geçti. Canlı çağrı/secret erişimi yapılmadı. Fix commit’i sonrası farklı fresh R2 yapılır.

### Adım 4 — İkinci fresh review ve kapanış

Head a148c78; farklı yeni ajanlar p02_step4_r2_contract / p02_step4_r2_safety sözleşme/uyumluluk ve güvenlik/kaynak/hata sınırlarını yeniden inceledi. Yeni doğrulanmış bulgu yok.77 test/19,51 s ve104 test/16,08 s; Ruff format/lint, strict mypy56,138 belge/6 skill/16 kart/diff geçti. Adım4 kod/review kapandı. Kullanıcı hazırlığı üzerinden sıradaki bağımsız iş bounded salt okunur live kabul ve Platform raw contract kontrolüdür; nihai kaynak/kurulum/performans kapısı açık kalır.

## Adım 5 — Platform raw kapısı ve ilk yetkili canlı gözlem

Kullanıcının hazırladığı0700/0600 Git dışı dosya yalnız ayrı pilot çocuk sürecinde okundu; seçili LLM env yalnız o süreçte aktarıldı. Ürün credentials.json okumaz. İlk pilot31 Ekim 02:30 Europe/Istanbul’da iki hizmet için ayrı yapıldı; payload/PII/header/key yayımlanmadı. LLM normal public API çağrısı geçerli typed terms cevabı verdi: accepted=false,current_version=1,is_material=true; selected account/project null, provider identity not_exposed/auth unknown ve terms_not_accepted ayrı kaldı. Süre0,259 s; bir mantıksal GET, ortak read-only en çok2 attempt politikası. Public API wire status’u dışarı vermediği için kesin HTTP kodu icat edilmedi. Şart kabulü/inference yapılmadı.

Platform yalnız GET /api/v1/auth/me: HTTP200,1036 body byte,0,120 s; root object, data object/message string/success bool alan tipleri gözlendi. Bu **raw shape gözlemidir**; logical success, principal/account anlamı, auth bağı veya tam şema kabulü değildir. Bilinmeyen schema’da durma kuralıyla organizations/projects/detail çağrılmadı. Bilinen account/project ID olmaması bu ilk çağrıyı engellemedi; otomatik seçim veya yeni kaynak yoktur.

İki hizmette de key’in sağlayıcıca teyitli syntax/length/prefix sözleşmesi yok; biçim tahminli negatif kontrol yapılmadı ve auth unknown kaldı. Negatif key registry’ye yazılmadı. Platform için endpoint/target/parametre-bound auth, principal/account semantics, envelope/pagination kapısı açık. Resmî sağlayıcı contract bağlantısı/konumu kullanıcıdan istendi; kullanıcı mevcut dataset entegrasyon kılavuzunu paylaştı. Bu kaynak zaten araştırmada sabittir; API kökü/header/önek ve dataset akışını destekler, me/org/project principal/envelope/paging sözleşmesi değildir. [Hazır destek talebi](../p02-account-setup.md#platform-sözleşme-kapısını-açmak) verildi; bu dış bilgi olmadan P02-0d veya P02-0b/P02-0 verified olmaz. LLM’nin bağımsız nihai kabulü sürer. Pilotun minimal maskeli receipt’i yerelde saklanır; ham hesap yanıtı saklanmadı/repoya alınmadı. Geçmiş araştırmadaki “icra edilmedi” bölümü planın tarihsel durumudur; bu bölüm yeni sınırlı icrayı kaydeder.

## Adım 6 — Bağımsız LLM nihai kaynak kabulü hazırlığı

Platform raw kapısı açıkken LLM kartının bağımsız kabulü tamamlanır; bütün P02-0 teslimi veya PR açılışı iddia edilmez. Desteklenen Linux/macOS state platformlarında iki temiz wheel/sdist kurulumundaki runtime-only isolated TLS smoke’a gerçek public discover eklendi; mevcut HTTP smoke ancak bu da geçerse passed olur. Typed terms/unknown kimlik/Platform tercih ayrımı ve secret/doc_path sınırı bağımsız oracle ile denetlenir, yeni discovery modüllerinin kurulum kökeni doğrulanır. Kaynak bağlı startup/jobs selector’ları P02-0 LLM referans adlarına hazırlanır; ölçüm tamamlanmadan referans kabulü yeşil sayılmaz. Kaynak hazırlığı94 hedefli installed-runtime/CI-matrix testiyle3,61 s’de geçti; yanlış selected/auth iddiası, bool/int coercion, eksik warning ve yanlış data tipi oracle tarafından reddedildi. Ruff format/lint171 dosya, strict mypy70 kaynak,138 belge/6 skill/16 kart/diff geçti. Son kaynakta tam test/statik/build/kurulum ve seri M5 ölçümü yapılacaktır; hazırlık commit’i iki fresh review turuna girer.

### Adım 6 — Birinci fresh review ve düzeltme

Head38ea022 üstünde p02_llm_final_r1_evidence / p02_llm_final_r1_contract yeni kurulum/oracle/CI/kanıt sınırlarını inceledi. P2 doğrulandı: discovery smoke’u koşulsuz state açtığından state desteklenmeyen platformda genel HTTP/stream kabulü de reddediliyordu. Worker seçimi mevcut verifier’ın Linux/macOS state sınırına hizalandı; HTTP/stream diğer platformlarda korunur. Parent-only platform facade ile gerçek isolated TLS worker koşuları state discovery’yi dışlayınca da başarılı olur; gerçek Windows koşusu iddia edilmez. P3: reference/card/current’ın bazı adım4 review ifadeleri kapanışla hizalandı. Ajanlar94 test/3,71–3,89 s ve statik/belge/ajan/diff geçti; Fix kaynakta95 test/5,22 s geçti; strict mypy70 kaynak,138 belge/6 skill/16 kart/diff temiz. Fix sonrası farklı fresh R2 yapılır.

### Adım 6 — İkinci fresh review ve kaynak kapanışı

Fix head29e4396 üstünde farklı yeni ajanlar p02_llm_final_r2_evidence / p02_llm_final_r2_contract R1 düzeltmelerini ve kurulum/oracle/kanıt/sözleşme sınırlarını inceledi. Yeni doğrulanmış bulgu yok.95 test/4,98–4,93 s; Ruff format/lint, strict mypy70 kaynak,138 belge/6 skill/16 kart/diff geçti. Ürün/test/ölçüm/workflow kaynak hazırlığı kapandı; şimdi tam takım, gerçek iki clean install ve seri kaynak bağlı M5 kabulü yapılır. İkinci tur Platform raw kapısını kaldırmaz ve planlanan ölçümü geçmiş saymaz.

## Bağımsız LLM yerel kabul kapanışı

**Kaynak:** 0e0d2b747d23976c46f196b02266a3ba1f6d6d8a. Tam takım koşusu38ea022 kaynak hazırlığında başladı ve **3.567 passed,1 skipped /555,90 s** verdi; atlanan Linux native counter testi macOS’ta ilan edilmiş platform sınırıdır. Bu koşu sırasında yalnız kurulum test aracının platform seçimi düzeltildi; ürün runtime baytları38ea022→0e0d2b7 arasında değişmedi. Değişen test aracı/oracle/CI seçimi ayrıca **95 test /5,22 s** ve iki fresh R2 koşusuyla4,98/4,93 s’de geçti. Böylece tam koşunun güncel test ağacında yeniden yapılmış olduğu iddia edilmeden ürün ve değişen kabul aracı kanıtı ayrılır. Son Ruff format/lint171 dosya, strict mypy70 kaynak,138 belge/6 skill/16 kart ve diff geçti.

Pinned uv0.11.2 wheel’i sdist’ten üretti. İki ayrı temiz runtime kurulumunda origin/basic/NDJSON/HTTP/stream/cache/execution/jobs geçti; HTTP smoke Linux/macOS’ta gerçek public LLM discovery/TLS/installed origin kontrolünü de içerir. Wheel62 üye SHA256 `7991df34efcc4dc6f2fae1a7a7a54859e48b4c9640085ff1e92b098451e959ab`; sdist392 üye SHA256 `623faa46785bccaa9d2b0dc7d4c2c3964fb167d964619203f9f984a3d24ed521`. [Kurulum arşivi](evidence.md#p02-0-llm-installation) final runtime’ı doğrular; sonraki belge/kanıt kapanışı bu tarihsel sdist’in içindeymiş gibi sunulmaz. Kullanıcı key dosyası/özel analiz/raw arşiv paketlerde yoktur.

Ölçümler test/build süreçleri bittikten sonra seri alındı: **Apple M5 Max/arm64,macOS27.0.1,Python3.11.18,internal SSD/APFS**. Gerçek runtime içeren bc9532c bağımsız taban checkout’u kullanıldı; A/A veya ilk-release fallback yoktur. Her komutta3 ısınma +30 ayrı süreç, bütün örnekler ve nearest-rank p95; OS cache’i boşaltılmış fiziksel soğuk açılış iddiası yoktur. [Startup](evidence.md#p02-0-llm-reference-startup) aday help/version/context/cache p95 **30,811/27,614/87,109/119,362 ms**; dört500/200 ms kapısı geçti. Taban p95 **34,150/27,915/84,730/117,960 ms** tanısaldır; göreli kazanç iddiası yoktur. Aynı kurulu adayla [jobs](evidence.md#p02-0-llm-reference-jobs) normal list/show **116,632/140,424 ms**, yoğun list/show **172,388/137,595 ms**; dört200 ms kapısı geçti. Kaynak/kurulum/fixture before-after eşliği korundu; workflow’nun iki zorunlu reference verifier’ı güncel tam kaynak baytlarıyla geçti. Üç yeni özgün JSON gzip/manifest/indeks ile kayıpsız saklandı; **152 arşiv** doğrulandı. Eski başarısız veya P01 kabulü yeniden etiketlenmedi.

[LLM P02-0c](../roadmap/tasks/p02-0c-llm-context-discovery.md) bu gerçek commit/test/review/ilk live/yerel referans kanıtıyla **yerel verified**. [Epik politikası](../roadmap/README.md#epik-başına-pr) alt işin aynı dalda yerel kapanışına izin verir; development teslimi veya paket/CI kapanışı değildir. Gerçek Linux3.11/3.14/macOS3.11 CI, yeni Linux raw/startup diagnostic ve bütünleşik kabul henüz çalıştırılmadı; tam P02-0 PR’ında kapanır. LLM terms sonucu auth/principal/izin verified üretmez; accepted=false güvenli geçerli gözlemdir, şart kabulü yapılmadı. Platform raw/auth/principal/envelope/paging dış kapısı açıkken P02-0d draft ve P02-0b/P02-0 bütünü tamamlanmamış kalır. Ayrı/eksik paket PR’ı açılmaz. Kapanış metni/manifest/referanslar ayrıca fresh kanıt review’sine girer.

### Yerel kapanış — Birinci fresh kanıt review’si

Head a884d98 üstünde p02_llm_closure_r1_evidence / p02_llm_closure_r1_status 152 arşivi, kaynak/kurulum/baseline/wheel eşliğini, gerçek p95’leri ve durum iddialarını inceledi. Ürün/kanıt doğruluğu kusuru yok. Bir P3 durum grubu doğrulandı: üst P02-0b kartında LLM yüzeyinin hâlâ yalnız tasarım olduğu ve son durum paragrafında LLM kodlamasının sürdüğü ifadeler kaldı. LLM yerel verified ile Platform/üst paket eksikleri ayrılarak düzeltildi; araştırma kartının eski “pilot yapılmadı” ifadesi araştırma kapsamına daraltıldı. İki verifier,152 arşiv,138 belge/6 skill/16 kart, Ruff171/strict mypy70 ve diff geçti. Fix sonrası farklı fresh kanıt R2 yapılır.

### Yerel kapanış — İkinci fresh kanıt review’si

Fix head b1cab29 üstünde farklı yeni ajanlar p02_llm_closure_r2_evidence / p02_llm_closure_r2_status kaynak/kurulum/baseline/örnek/p95/152 arşiv ve current/kart/ref sınırlarını inceledi. Ürün veya ölçüm doğruluğu bulgusu yok. Son P3: P02-0b üst kartının teslim kaydı dip paragrafında eski genel “henüz uygulanmadı” ifadesi kalmıştı; gerçek LLM commit/kabul bağı ve açık Platform/üst paket/PR/CI sınırıyla düzeltildi. Güncel P02-0 kart/plan/ref için benzer şimdiki zaman iddiaları hedefli tarandı.152 arşiv, iki güncel reference verifier,138 belge/6 skill/16 kart ve diff geçti. İki fresh kanıt turu kapandı; runtime/test/ölçüm/workflow kaynağı değişmedi, yeni ölçüm gerektiren kaynak farkı yoktur.

## Açık kapı ve sonraki adım

[Accepted ADR-0020](../decisions/0020-service-bound-context-discovery.md) onay kapısı kapandı; [LLM referansı](../reference/context-discovery.md) bağımsız uygulamayı tarif eder. LLM yerel verified; Platform raw/key/principal/envelope/paging ve kendi live kabulü dış koşulları açık. Kullanıcının sağladığı dataset kılavuzu bu kimlik/proje sözleşmesini kapatmadı; hazır destek talebi verildi. P02-0a araştırması P02-0b veya P02-0 bütününü tamamlanmış yapmaz. Ayrı belge PR’ı açılmaz; nihai development PR bütün kod/adım review/yerel kabul kapıları tamamlanınca açılır; PR’ın üç ortam CI ve bütünleşik kabulü ardından kapanır.

## 31 Ekim devamı — Platform araştırması ve önerilen başlangıç kapısı

Kullanıcı devamı yetkilendirdi. Yeni [metadata survey](p02-platform-discovery-observations.md) me 200/success=true, organizations 200/items 1/total alanı ve projects 200/boş dizi gözledi; üç GET 0,193011 s ve 1.350 body byte. İlk özetleyicideki tip hatası başarısız kayıt olarak korundu; ağsız sentetik privacy/shape/limit kontrolü sonrası düzeltildi. Devam serisinin iki tek-endpoint girişimi ve üç-GET survey’i toplam 5 mantıksal GET başlattı; birikimli seri ADR-0020’nin 4 pozitif GET/30 s contract-pilot tavanını sağlamadı. Bu sapma ve ayrı son-survey bütçesi araştırma notunda açıkça kaydedildi; seri contract kabulü sayılmadı ve yeni hesap çağrısı yapılmadı. Bu kontroller ürün testi veya tam hizmet/auth kabulü değildir.

[ADR-0021](../decisions/0021-platform-discovery-observations.md) ve [kapalı Platform proposal’ı](../reference/context-discovery.md#önerilen-platform-gözlem-varyantı) bağımlı ürün kodundan önce hazırlandı. Öneri unverified projeksiyon implementasyonunu açar; P02-0d/P02-0b/P02-0 verified koşullarını değiştirmez. Kullanıcının yeni ADR’ler için önceden onay isteme talebi nedeniyle ürün kodu başlamadı; Accepted ADR-0020 halen bağlayıcıdır. Commit sonrası iki fresh belge/kanıt review turu yapılır. Runtime/test/ölçüm/workflow değişmedi; LLM yerel referanslarını yeniden ölçmek gerekmiyor.

### ADR-0021 — Birinci fresh belge/kanıt review turu

Head5bbf2f5 üstünde adr21_r1_contract / adr21_r1_safety önerilen partial amendment, strict public wire, secret-before-projection, bütçe/gerçek gözlem ve değişmeyen verified kapısını inceledi. Tek P2 doğrulandı: organizations items/total yanında root success=false/non-bool bayrağının metadata diye atılabileceği belirsizdi. Tüm root object’lerde success varsa strict bool=true ön koşulu açıkça yazıldı; mixed valid-items+false/yanlış-tip fixture’ları istendi. Henüz ürün kusuru veya uygulanmış fix iddiası yok; proposal düzeltmesidir.140 belge/6 skill/16 kart,152 arşiv, iki mevcut LLM reference verifier ve diff geçti.

Kullanıcının yeni Platform chatbot cevabı ayrıca mevcut receipt ve güncel resmî kamu istemcisi/kılavuzuyla karşılaştırıldı; me/organization/project ID alan adları uyuşmuyor, pagination/VIEW/key-grammar ve doğrudan Swagger adresi teyitsiz. Provider ile yeni hesap çağrısı yapılmadı. Önceki kullanıcı özetindeki total=1 ifadesi düzeltildi; kayıt yalnız item count1 ve total integer türünü kanıtlar. Karşılaştırma ve yeni primary asset kimlikleri araştırma/kanıt kaydında tutuldu. Bu açıklama ADR-0021’i Accepted yapmaz veya mevcut gate’i kapatmaz. R1 fix sonrası farklı fresh belge/kanıt R2 yapılır.

### ADR-0021 — İkinci fresh belge/kanıt review turu

Fix head7716c45 üstünde farklı yeni ajanlar adr21_r2_contract / adr21_r2_safety kapalı Platform wire/projeksiyon, tercih/bildirilen ID/yetki ayrımı, root logical failure, kaynak ve kanıt sınırlarını yeniden inceledi. Yeni doğrulanmış bulgu yok.140 belge/6 skill/16 kart/diff,152 metric arşivi, iki güncel LLM source-bound verifier, metadata receipt hash/3 çağrı/1.350 byte/0,193011 s ve kamu asset byte/hash eşliği geçti. Chatbot’taki id alan adları ve teyitsiz pagination/VIEW/OpenAPI iddiaları doğru ayrılmış; total sayısal değeri türetilmiyor.

Öneri kullanıcı onayına hazırdır. ADR-0021 Proposed; Accepted ADR-0020 yürürlükte, P02-0d draft ve Platform ürün çağrısı unsupported_combination olarak kalır. Onay sonrası aynı dalda planlanan iki kod dilimi ve her dilimin iki fresh review turu uygulanabilir; tam auth/principal/pagination/dolu-seçili proje ve paket/PR/CI kabul kapısı halen korunur. Bu doküman turunda ürün testleri veya yeni performans ölçümü çalıştırılmadı; runtime/test/ölçüm/workflow baytları değişmedi.

## 1 Kasım — ADR-0021 kullanıcı review bulgularının doğrulanması

Kullanıcı yanıtı onay değil, belge/sözleşme review’sidir. ADR-0021 Proposed, ADR-0020 Accepted ve Platform ürün yolu unsupported_combination olarak kalır. Bu tur yalnız yetkilendirilmiş belge düzeltmesidir; account çağrısı veya ürün kodu yoktur.

- Ara metadata istisnası ile nihai unknown-ret kabulü çatışması doğrulandı: ara projeksiyon ve nihai kabul ayrıldı. P02-0d’nin final verified durumu için **gerçek üretim consumer’ında katı decoder’a ek kod geçişi**, raw unknown ret/fallback yasağı ve tüm dış kabul kapıları zorunlu; ara kod/test tek başına kapanış değildir. Plan5.3 açık zorunlu adım oldu.
- “Tüm PII dışarıda” ifadesi daraltıldı: ad/email/telefon ve tüketilmeyen profil/role alanları atılır; reported ID’ler kişiye bağlanabilir. Public wire’ın kullanıcı çıktısı olduğu ve paylaşım/saklamada tanımlayıcıların korunacağı açıklanır; Identifier bir PII sınıflandırıcısı değildir.
- Receipt/parser uyumu ayrımı doğrulandı: tür metadata’sı Identifier veya total aralık/eşitsizlik predicate’lerini ve nonempty/detail kabulünü kanıtlamaz. ADR ve araştırma notu bunu açık söyler; eski JSON receipt’in hash/baytları değişmedi. 5 GET ve4 pozitif GET/30 s tavanı sapması ADR’nin kanıt özetine de eklendi; 0,193011 s yalnız son survey’dir, gerçek attempt sayısı ölçülmedi, 3 MiB survey ile 4 MiB ürün bütçesi karıştırılmaz.
- Profil-only proje seçimi boşluğu kapatıldı: profil veya explicit override’dan gelen selected.project_id detail GET’ini tetikler; 4 GET/4 observation. Seçim yoksa 3. Orijinal profile_preference korunur. Aynı fixture selected/pref/state/çağrı sayısını birlikte doğrulayacak.
- State/reason sözlüğü birleştirildi: genel selection_required/selection_unverified/unverified/mismatch kavramları için tek wire/error tablosu ve tam sentetik Result JSON’u yazıldı. Detail404 not_found + selected_project_not_found + validation=unverified; yanlış detail ID invalid_response; parent farkı iki kaynağı koruyan unverified gözlem. Reasons ASCII sözlük sırasındadır; eski kavramsal adlar yeni wire reason değildir.
- Me için success/data zorunluluğu açıklaştırıldı. Success eksik,false,0,1,"true" me negatifleri; organizations opsiyonel-success ve detail bare/zarf ayrımı ayrı fixture’larla tanımlandı.
- Onay commit’i için ADR-0020/0021, karar indeksi, referans, P02-0d/0b, plan/current/task indeksi geçiş listesi yazıldı. Şimdi yalnız koşullu açıklamalar hizalandı; onay alınmış veya kart ready olmuş sayılmadı.
- API dönüş/renderer bulgusu doğrulandı. **Önerilen Result[A|B] şekli aynen alınmadı:** gerçek Result invariant olduğu için izole strict-mypy deneyi iki implementation-return hatası verdi. Literal overload’lar korunup generic dönüş Result[A]|Result[B] seçildi; aynı deney geçti ve service_id ile data narrowing iki varyantta doğrulandı. Bu statik tip deneyi planned Platform modelinin ürün uygulaması veya bütün ürün testi değildir. Ortak Result variance/wire değişmedi; iki DTO renderer dispatch ve service_id discriminator’ı referansta koddan önce tanımlı.

Düzeltme commit’i sonrası iki farklı fresh belge/kanıt review turu yapılır. Kullanıcı onayı gelmeden Accepted veya ürün implementasyonu yoktur. Runtime/test/ölçüm/workflow kaynakları değişmedi; bu belge turu için tam ürün/performance takımı tekrar çalıştırılmaz.

Düzeltme ön doğrulaması:140 public Markdown,6 skill/16 kart ve diff geçti. Tam sentetik404 Result örneği JSON olarak parse edildi;21 data alanı, tam reason kümesi/ASCII sırası, profile-only seçili ID,4 endpoint/resource/outcome, canonical zaman sırası, UUIDv4 binding ve output sınırı bağımsız kontrol edildi. Python imza fence’leri syntax kontrolünden geçti. İki izole mypy alternatifinden invariant-wrapper union beklenen2 hatayı verirken union-of-results geçti; bu bir ürün testi değildir. Özgün receipt3031 byte/SHA değişmedi.152 arşiv ve iki güncel LLM kaynak referansı doğrulandı. Commit sonrası fresh R1/R2 henüz bu revizyonun yeni kapanışını oluşturacak.

### 1 Kasım revizyonu — Birinci fresh belge/kanıt review turu

Head7353637 üstünde adr21_revision_r1_contract / adr21_revision_r1_safety kullanıcının yeni bulgularının düzeltmelerini bağımsız inceledi. Yeni doğrulanmış bulgu yok. Ara metadata/nihai üretim katı decoder ayrımı, profilden veya override’dan detail4GET, tek seçim/reason sözlüğü, parent farkı ve ID-route hatası, me başarı alanı zorunluluğu, linkable-ID gizlilik tanımı ve gerçek şekil kanıtı sınırı tutarlı bulundu. Union-of-results API tasarımı ve tam sentetik404 Result alan/zaman/reason eşliği doğrulandı.

140 belge/6 skill/16 kart/diff,152 arşiv, iki güncel LLM kaynak referansı ve özgün receipt3031 byte/SHA eşliği geçti. Ürün testi/benchmark veya canlı hesap çağrısı yapılmadı; runtime/test/ölçüm/workflow değişmedi. ADR-0021 halen Proposed; bu revizyon için farklı fresh ajanlarla ikinci tur yapılır.

### 1 Kasım revizyonu — İkinci fresh belge/kanıt review turu

Head d8b5528 üstünde farklı yeni ajanlar adr21_revision_r2_contract / adr21_revision_r2_safety tüm revizyonu bağımsız inceledi. Yeni doğrulanmış bulgu yok. Ara projeksiyon ile zorunlu nihai üretim katı decoder/fallback yasağı, profil veya explicit seçimde4 GET, tek404/reason/error sözlüğü ve parent farkında unverified sonucu, me/org/detail success varlık kuralları, linkable-ID gizlilik sınırı ve onay geçiş listesi tutarlı bulundu. Invariant Result için union-of-results, varyant renderer/discriminator ve tam sentetik404 JSON21 alan/reason/zaman/UUID eşliği doğrulandı.

140 Markdown/6 skill/16 kart/diff,152 arşiv ve iki güncel M5 kaynak referansı geçti; metadata receipt3031 byte ve SHA değişmedi. Ürün testi/benchmark veya account çağrısı yapılmadı; runtime/test/ölçüm/workflow kaynakları aynı kaldı. Revize ADR-0021 tekrar kullanıcı onayına hazırdır; kullanıcı review yanıtı onay sayılmadı, Proposed statüsü ve P02-0d draft/Platform unsupported davranışı korunur. Gerçek onay alınırsa belirtilen belge geçişleri koddan önce tek commit’te uygulanır.

## ADR-0021 onayı ve Platform ara uygulaması

Kullanıcı revize ADR-0021’i 2026-11-01 tarihinde açıkça onayladı ve uygulamayı yetkilendirdi. 9fae321 onay commit’i ürün kodundan önce karar/referans/indeks/plan/kart/faz/current geçişlerini yaptı; doküman ve kart denetimleri geçti. ADR-0020 yalnız ara başlangıç/metadata ve Platform wire eşlemesinde kısmen değişti; nihai üretim katı decoder ve gerçek auth/principal/pagination/dolu-seçili proje kabulü açık kalır. P02-0d ara uygulama in_progress, aggregate P02-0b draft; yeni PR veya canlı hesap çağrısı yoktur.

### Adım 5.1 — Kapalı Platform çekirdeği ve gerçek HTTP/state sınırı

Kapalı Platform DTO’ları ID bildirimi/tercih/kimlik/yetkiyi ayırır. Bütün raw-tree strict JSON/sır taraması, tüketilmeyen metadata atımından önce yapılır; ortak closed codec gevşetilmez. Tek owned session, X-API-Key, üç GET ve profil/override seçimi varsa dördüncü detail GET uygulanır. 404 gözlem, parent farkı, missing/null parent ve tam sıralı reason sözlüğü korunur. Yeni DB/cache/schema yoktur.

Mevcut capture/network/cleanup/final gate genel tipli exchange olarak paylaşılır; StateDiscovery hizmet parametresi ve aynı config snapshot’ından orijinal profil tercihlerini taşır. LLM anlamı korunur. Public API/CLI bağlantısı adım 5.2’dir; bu commit o yüzeyi henüz açmaz.

Ön doğrulama: 87 bağımsız Platform sözleşme/projeksiyon testi; 24 gerçek TLS/SQLite entegrasyon testi geçti. Entegrasyonlar üç/dört GET, profil/override ayrımı, 401/403/404/429, secret metadata, oversize/logical/shape/route-ID retleri, shared deadline/cleanup/cookie sınırı, no-init ve iki ayrı endpoint’te ayrı süreç credential/reset/clock-generation yarışını kapsar. Önceki LLM sözleşme/çekirdek ve mimari regresyonları 313 testle geçti (32,92 s). Ruff format/lint, strict mypy (60 kaynak), 140 belge/6 skill/16 kart ve diff geçti.

İlk yeni test koşusunda registry’nin meşru env referans adı kaydı yanlışlıkla raw secret ile aynı yasak gibi assert edildi; test oracle’ı düzeltildi. 429’un mevcut read-only iki denemesi de doğru çağrı sayısıyla assert edildi. Bu ilk başarısız koşu başarı olarak sunulmaz; ürün kuralı bu nedenle değiştirilmedi. Tam takım/iki kurulum/yeni M5 kaynak referansı henüz koşulmadı; eski LLM referansları yeni kaynak kabulü değildir. Commit sonrası iki farklı fresh kod review turu sıradadır.
