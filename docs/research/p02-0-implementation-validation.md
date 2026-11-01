# P02-0 uygulama ve review kaydı

**Tarih:** 2026-10-31. **Güncellendi:** 2026-11-01. **Durum:** P02-0 ve P02-0a/0b/0c/0d çalışma dalı kabulü verified. ADR-0020/0021/0022 Accepted; LLM ve Platform dar gözlemi, ayrı canlı consumer kabulleri, her adımın iki fresh review turu, kaynak bağlı M5 ve üç ortam source CI tamamlandı. [PR #12](https://github.com/HodeTech/Yorunge/pull/12) kullanıcı review/merge bekler; development teslimi/yayın değildir. [Güncel Sonar/native merge takibi](#sonar-ve-native-merge-kapısı-takibi) son çalışmayı taşır; önceki CI/paket kapanışları tarihsel kaynaklarıyla korunur. Aşağıdaki önceki Proposed/onay-bekleme, yapılmadı/açık/blocked ve eski katı decoder zorunluluğu ifadeleri kendi tarihsel aşamasını anlatır; güncel karar ADR-0022 ve son kapanış bölümüdür. **Dal/taban:** feat/p02-0a-sdk-pilot / development bc9532c. [Paket planı](../roadmap/p02-0-delivery-plan.md).

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

[ADR-0021](../decisions/0021-platform-discovery-observations.md) ve [kapalı Platform proposal’ı](../reference/context-discovery.md#platform-gözlem-varyantı) bağımlı ürün kodundan önce hazırlandı. Öneri unverified projeksiyon implementasyonunu açar; P02-0d/P02-0b/P02-0 verified koşullarını değiştirmez. Kullanıcının yeni ADR’ler için önceden onay isteme talebi nedeniyle ürün kodu başlamadı; Accepted ADR-0020 halen bağlayıcıdır. Commit sonrası iki fresh belge/kanıt review turu yapılır. Runtime/test/ölçüm/workflow değişmedi; LLM yerel referanslarını yeniden ölçmek gerekmiyor.

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

### Adım 5.1 — Birinci fresh kod review turu

5b3a4d5 için iki bağımsız yeni ajan (platform_core_r1_safety, platform_core_r1_contract) güvenlik/lifecycle ve sözleşme/DTO/test boyutlarını inceledi. Tek P2 doğrulandı: detail raw taraması bare ve success/data zarfının sabit anahtar muafiyetlerini birleştiriyordu. Zarf kökündeki id/org_id veya bare nesnedeki data alt ağacının tüketilmeyen anahtarları kısa-secret taramasından muaf kalabiliyordu; public çıktıya sızıntı gösterilmedi. Muafiyet root success varlığıyla seçilen şekle daraltıldı; dört negatif ve iki geçerli bare/zarf oracle eklendi.

Düzeltme sonrası 93 contract +24 gerçek TLS/SQLite =117 test (18,64 s), lint/format ve strict mypy geçti. Güvenlik ajanı ayrıca ortak LLM cleanup/rollback/cancel/deadline/active-loop kümesinde10 testi bağımsız geçirdi; diğer yeni kusur yok. Farklı fresh ajanlarla ikinci tur bu düzeltme commit’inden sonra yapılır. Canlı hesap veya ölçüm çağrısı yoktur.

### Adım 5.1 — İkinci fresh kod review turu

cf02470 üzerinde farklı yeni ajanlar platform_core_r2_safety / platform_core_r2_contract cumulative çekirdeği bağımsız inceledi; yeni doğrulanmış bulgu yok. R1 şekil-bağımlı anahtar muafiyeti düzeltmesi doğrulandı. İki ajan ayrı117 Platform testini (20,08/20,59 s) geçti; sözleşme ajanı ayrıca338 LLM/API/CLI/mimari regresyonu (45,14 s) ve14 salt bellek adversarial DTO kontrolünü geçti. Hedef/credential, no-init, shared deadline, cleanup/final epoch-generation kapısı, exact wire ve unknown yetki sınırı korundu. Adım5.1 iki review turuyla kapandı; public bağlantı5.2 sıradadır. Tam kaynak/paket/ölçüm ve nihai dış kabul kapıları bu turla kapanmış sayılmaz. Canlı çağrı veya reviewer dosya değişikliği yoktur.

### Adım 5.2 — Public API/CLI ve kurulu ürün consumer’ı

Python literal LLM/Platform overload’ları dar Result tiplerini korur; generic ServiceId union-of-results döndürür, Result invariantlığı/v1 wire’ı değiştirilmez. İzole strict-mypy assert_type programı iki literal/generic dönüşü ve data.service_id ile narrowing’i doğruladı. State/config/secret aynı kullanımdan gelir; public Platform çağrısı artık ara unverified çekirdeğe bağlıdır. İki DTO’ya göre text renderer, JSON/NDJSON/UTF-8, ID gizlilik ve yetki/tamlık uyarıları eklendi; README/kanonik CLI/reference güncellendi.

Gerçek CLI çocuk süreçleri ve public API, profile-only/explicit seçim, detail404, aynı config’in bir defa okunması, tek hizmet env’si, default/explicit no-init state, machine hata zarfı, SIGINT ve kapalı stdout ile sınandı. Önceki unsupported testinin offline fixture’ı HTTP importlarını kasıtlı yasaklıyordu; Platform artık desteklendiği için bu eski gate testi kaldırıldı. Aynı no-init beklentisi yeni gerçek CLI eksik-store testiyle ve sıfır request assertion’ıyla korunur; offline import guard gevşetilmedi. Yerel context’in Platform modelini eager import etmediği kontrol de eklendi.

Runtime-only izole kurulum harness’ına Platform discovery case’i eklendi: gerçek TLS, kurulu public API, dört GET, yalnız X-API-Key, kritik wire alanları için bağımsız sabit oracle ve yeni modüllerin kurulu prefix kökeni doğrulanır. Desteklenmeyen state OS’unda yalnız HTTP/stream testleri çalışır; gerçek Windows kabulü iddia edilmez. 37 harness testi geçti (4,82 s). Yeni/LLM public yüzey + core boundary + CI matrix307 testi geçti (26,09 s). Lint/format, strict mypy (60 kaynak + ayrı tip deneyi), belge/kart ve diff kontrolleri geçti.

CI verifier seçimleri yeni p02-0-platform-reference startup/jobs adlarına taşındı; bu commit’te bu yeni ölçümler henüz üretilmedi. Eski LLM kaynak referansı yeni ürün kabulü yerine kullanılmaz. İki fresh review turundan sonra kaynak dondurulup tam takım, iki gerçek temiz kurulum ve yeni M5 ölçümleri alınacak; o zamana kadar uzak CI/nihai PR açılmaz. Nihai katı decoder/auth/live kapısı ve P02-0d/P02-0b verified işi açık; canlı hesaba yeni istek gönderilmedi.

### Adım 5.2 — Birinci fresh kod review turu

İki yeni ajan platform_public_r1_contract / platform_public_r1_evidence eb8b94c için API/CLI ve kurulu consumer/kanıt sınırını bağımsız inceledi. P2 text semantiği doğrulandı: opak me_id, kullanıcı principal’ı gibi adlandırılmamalıydı; etiket Bildirilen auth/me ID olarak düzeltildi. P3 eski Proposed/uygulanmadı aktif özetleri, CLI help ve plan/kart ifadeleri Accepted/ara uygulama durumuyla hizalandı; tarihsel araştırma kayıtları değişmedi. CliResult alias’ına Platform Result eklendi; argparse service açık ServiceId cast’iyle generic overload dönüşüne bağlandı. Salt metadata help testi iki hizmeti ve yetki sınırını IO guard altında doğrular.

Düzeltme sonrası286 public/LLM/core/kurulum-harness testi (29,25 s) ve ayrı yeni help testi geçti. Mypy gerçek CLI union dönüşünü ve iki literal/generic/narrowing deneyini geçti; belge/kart/diff kontrolleri temiz. Ajanlar bağımsız35 public/lazy ve48 public/kurulu testini geçirdi; ek runtime kusuru bulmadı. İlk help assertion’ı argparse satır kaydırmasını boşluk normalizasyonuyla hesaba katacak şekilde düzeltildi; yardım metni veya IO guard gevşetilmedi. İkinci fresh tur farklı ajanlarla bu fix commit’inden sonra yapılır. Canlı hesap çağrısı yoktur.

### Adım 5.2 — İkinci fresh kod review turu ve kaynak dondurma

87ad0b5 için farklı yeni ajanlar platform_public_r2_contract / platform_public_r2_evidence cumulative public ve kurulu consumer değişikliğini inceledi; yeni doğrulanmış bulgu yok. R1 opak kimlik etiketi, Accepted/help/durum ve CliResult düzeltmeleri kapalı. Bağımsız250 public/LLM/core test (25,84 s) ve264 public/kurulu/core test (17,37 s) geçti. Review salt okunur ve sentetik TLS ile yapıldı; tam takım/iki gerçek kurulum/M5 veya canlı hesap kabulünün yerine sayılmaz.

İki ara kod adımı her birinde commit + iki fresh review turuyla kapandı. Bu belge commit’inden sonra ürün/test/workflow kaynakları dondurularak tam takım, wheel/sdist iki temiz runtime kurulumu ve yeni kaynak bağlı M5 startup/jobs kabulü yapılır. Bağımsız LLM’nin eski kaynak kanıtları tarihsel kalır. Nihai üretim katı decoder ve dış hizmet kabulü halen açık5.3’tür; bu freeze P02-0d/0b verified ilanı değildir.

## Platform ara yerel kabul kapanışı

**Kaynak:** 0b05a64178fcae03a846fff5a9f68a36fa032005. İki kod adımı ve her birinin iki farklı fresh review turu yukarıda kapandı. Kaynak dondurulduktan sonra tam takım **3.695 passed,1 skipped /570,87 s** verdi; tek skip macOS’ta Linux native counter regresyonudur. Bu tam koşuda ürün/test/workflow değişmedi. Ruff format/lint187 dosya, strict mypy74 kaynak, ayrı literal/generic/narrowing deneyi,140 belge/6 skill/16 kart ve diff geçti. Üç ortam CI veya gerçek Windows kabulü iddia edilmez.

Pinned uv0.11.2 wheel’i sdist’ten oluşturdu. İki gerçek temiz runtime kurulumunda origin/basic/NDJSON/HTTP/stream/cache/execution/jobs geçti; HTTP harness hem LLM hem **Platform gerçek TLS/public API** yollarını çalıştırdı. Platform’da dört tam route, yalnız X-API-Key, kritik bağımsız wire/secret/PII oracle ve kurulu yeni modül prefix’i denetlendi. Wheel66 üye SHA256 `ca9597cdd9673100dc40208f10a4fbe8b514b3f967abd5486229b141087465ef`; sdist402 üye SHA256 `04081c6860d6ea691637b43441f9749202774a2497373f98a71e52c52ec0c004`. [Kurulum receipt’i](evidence.md#p02-0-platform-installation) özgün çıktıları saklar. Kullanıcı key dosyaları, özel analiz ve raw gzip arşivler paket üyesi değildir. Sonraki belge/kanıt kapanışı bu tarihsel sdist’in içindeymiş gibi sunulmaz; paket yayını yapılmadı.

Test/build süreçleri bittikten sonra ölçümler seri alındı: **Apple M5 Max/arm64,macOS27.0.1,Python3.11.18,internal SSD/APFS**. Startup aynı-host gerçek runtime tabanı bc9532c ile eşli AB/BA’dır; A/A fallback yok. Her komutta3 ısınma +30 ayrı süreç, bütün örnekler ve nearest-rank p95 korunur; fiziksel soğuk boot veya bütün host’larda kesin süre garantisi değildir. [Startup](evidence.md#p02-0-platform-reference-startup) aday help/version/context/cache p95 **27,385/29,398/89,282/127,984 ms**; özgün500/200 ms kapıları geçti. Taban p95 **26,293/31,815/92,977/126,559 ms** tanısaldır; göreli kazanç iddia edilmez. Aynı kurulu adayla [jobs](evidence.md#p02-0-platform-reference-jobs) normal list/show **117,479/113,095 ms**, yoğun list/show **155,282/124,982 ms**; dört200 ms kapısı geçti. Kaynak/kurulum/fixture before-after eşliği ve workflow’nun iki yeni reference verifier’ı güncel kaynak baytlarıyla geçti.

Üç yeni özgün JSON kayıpsız gzip/manifest/indeks ile saklandı; **155 arşiv** doğrulandı. Önceki LLM ve başarısız kaynak kayıtları tarihsel korunur; yeniden etiketlenmedi. Özgün Platform metadata receipt’i değiştirilmedi. Bu uygulama sırasında yeni canlı hesap çağrısı veya key/negatif kontrol üretilmedi; TLS fixture başarısı gerçek sağlayıcı kabulü değildir.

**Açık5.3:** Sağlayıcının sürüm/hedef/endpoint kapsamlı raw/key-auth/principal/pagination sözleşmesi olmadan üretim katı decoder, endpoint başına yetkili iyi biçimli negatif kontrol ve dolu/seçili proje live kabulü tamamlanamaz. Ara projeksiyona fallback yasağı korunur. Bu nedenle P02-0d blocked; P02-0b draft, P02-0 partial kalır. LLM verified alt teslimi geri alınmaz. Bir sonraki kod/kabul işi bu somut dış sözleşmeyi tüketen5.3’tür; P02-1 veya başka faz işi başlatılmadı. Tek nihai P02-0 development PR bütün kabul kapanınca açılacak; şu an PR/CI/merge/release iddiası yoktur. Kapanış kanıtı için fresh salt-okuma review turları sıradadır.

### Platform yerel kabulü — Birinci fresh kapanış review turu

af0f856 için farklı yeni ajanlar platform_acceptance_r1_proof / platform_acceptance_r1_docs kaynak/kurulum/ölçüm kanıtını ve aktif teslim belgelerini bağımsız inceledi. P3 üst P02-0b kartının eski Platform discovery yok/ready ifadeleri doğrulandı; ara uygulama/yerel kabul tamamlandı, nihai5.3 blocked ve aggregate draft olarak hizalandı. Ürün veya kabul kaynağı değişmedi.

155 arşiv, iki yeni kaynak bağlı M5 verifier,140 belge/6 skill/16 kart ve diff geçti. Proof ajanı iki özgün kurulum JSONL kaydını artifact hash/üye sayılarıyla, sdist’ten wheel build logunu ve tam takımın özgün3.695/1skip/570,87 s logunu karşılaştırdı; sayı/ortam/kaynak/kritik installed consumer iddiaları uyumlu. Test/build/benchmark veya canlı çağrı tekrarlanmadı. Farklı fresh ajanlarla ikinci kapanış turu bu belge fix commit’inden sonra yapılır.

### Platform yerel kabulü — İkinci fresh kapanış review turu

5aa611e üzerinde farklı yeni ajanlar platform_acceptance_r2_proof / platform_acceptance_r2_docs cumulative kapanış kanıtlarını ve aktif belgeleri bağımsız inceledi; yeni doğrulanmış bulgu yok. R1 üst kartın eski yok/ready anlatımı kapandı. Ara yerel kabul ile nihai5.3 katı decoder/auth/principal/pagination/live kapısı, blocked/draft/partial ve ayrı LLM verified durumu tutarlı.

155 kayıpsız arşiv, iki yeni current-source M5 verifier,140 belge/6 skill/16 kart ve diff geçti. Proof ajanı özgün full-suite/build/iki kurulum loglarını, artifact SHA/66–402 üyelerini ve private/raw dışlamasını, startup/jobs aday wheel eşliğini ve gerçek bc9532c baseline’ını karşılaştırdı. Kaynak/test/script/workflow/lock baytları0b05a64’ten beri değişmedi; yeni test/build/benchmark veya canlı hesap çağrısı çalıştırılmadı. Bu ara uygulama ve yerel kabul kapanmıştır; nihai5.3 dış kapısı nedeniyle üst P02-0 tamamlanmış sayılmaz. GitHub’da bu dal için açık PR bulunmadığı kapanışta connector ile doğrulandı; nihai development PR kabul kapısı kapanınca açılır.

## ADR-0022 review revizyonu ve mevcut consumer’ın seçili-proje kabulü

[Kanıt ve revizyon kaydı](p02-platform-reverse-engineering.md#kullanıcı-adr-0022-review-bulgularının-revizyonu) özgün kimlik/bağ ihtiyacı P02-R1/B14 sahibini, değişmez özgün probe/19 test kaynağını, literal-secret kapsamını ve madde/dosya geçiş eşlemesini kapatır. 70e60f8/f66a897 revizyonu iki farklı fresh contract/probe review turundan geçti; yeni doğrulanmış bulgu yok. Ana incelemenin son cleanup deadline kapısı 10 sentetik probe vakasında sınandı; mevcut 93 consumer + 19 arşiv + 10 yeni vaka birlikte **122 passed / 2,43 s**.

Kullanıcının kendisinin hazırladığı private test projesi ile mevcut Accepted ara gözlem yolunun [ayrı canlı kabulü](p02-platform-reverse-engineering.md#seçili-proje-canlı-kabulü--ayrı-koşu) f66a897 üzerinde bir kez çalıştı: 4 ürün GET’i 200; sadece yeni detail missing-key kontrolü 401; 5 GET/5 attempt/2.090 byte/0,488645 s. Nonempty liste, seçili ID/detail eşliği ve unknown/unverified/no-authority predikatlarının tamamı geçti. ID/key/raw/PII değerleri yerine [şekil/sayaç/predikat receipt’i](p02-platform-selected-project-observations.json) ve sürümlü yöntem kaynakları korunur. Önceki 6 GET koşusu değiştirilmedi; iki koşu tek contract pilotu diye sunulmaz.

Bu gerçek consumer/live sonucu ADR-0022 onayı, doğrulanmış key/principal/permission veya whole-raw nihai katı decoder değildir. Aktif Accepted ADR-0020/0021 kapısı, P02-0d blocked/P02-0b draft/P02-0 partial ve tek nihai PR/üç ortam CI koşulu korunur. Kaynak runtime/test/script/workflow baytları değişmedi; mevcut iki M5 verifier ve 155 arşiv geçti. 143 public Markdown/6 skill/17 kart ve ayrıca iki nested kaynak README kontrol edildi. Tam ürün takımı ve iki kurulu runtime kabulü bu belge/research değişikliğinde tekrarlanmadı; önceki kaynak kanıtı yerine yeni ölçüm iddia edilmez.

## ADR-0022 onayı ve nihai kabul geçişi

Kullanıcı revize ADR-0022’yi 2026-11-01 tarihinde açıkça onayladı ve devamı yetkilendirdi. Aynı onay commit’inde ADR-0020/0021 ileri notları, karar indeksi, kanonik referans/anchor’lar, P02-0b/d/P02-R1, plan/current/faz/matris ve kullanıcı belgeleri madde eşlemesine göre hizalandı. Ayrı whole-raw decoder/formal auth-principal-pagination kapısı kaldırıldı; geçmiş kabul başarısı diye kaydedilmedi. Doğrulanmış kimlik/bağ ihtiyacı P02-R1/B14’te açık kalır; sonraki yan etkili tüketicilerin otorite/onay sınırı aynıdır.

Mevcut gerçek consumer yeni nihai sözleşmeyle aynı davranışı zaten uygular; ortak codec veya runtime mantığı gevşetilmedi. platform_projection modül açıklaması nihai dar observer sınırını anlatacak şekilde değişti. Bu Python bayt değişikliği ve yeni workflow/test referans adları source-bound manifesti etkiler. Son referans adları ölçümden önce p02-0-final-reference-startup.json ve p02-0-final-reference-jobs.json olarak sabitlendi; eski yeşil M5 kanıtı bu yeni kaynağın kabulü sayılmaz. Yeni ölçümler henüz üretilmediği için onay commit’i tek başına yeşil CI iddia etmez; PR ancak son kaynak kanıtlarıyla açılacaktır.

Kart denetimindeki aggregate bağımlılık koşulu korundu: Platform P02-0d in_progress, ona bağımlı P02-0b draft; Platform verified olmadan üst kart STARTABLE yapılmadı. Bu onay adımı da commit ve iki farklı fresh contract/code/kanıt review turuyla kapanır. Canlı hesap deneyi tekrarlanmayacak; mevcut 6 ve 5 GET koşularının kaynak/yöntem ve no-authority sınırı korunur.

### ADR-0022 kabul geçişi — birinci fresh review turu

92c358a üstünde yeni ajanlar adr22_accept_r1_contract ve adr22_accept_r1_proof sözleşme/roadmap geçişini ve gerçek tüketici/kanıt sınırını bağımsız inceledi. Üç belge bulgusu doğrulandı ve 9da10dd ile kapatıldı: paket planındaki iki eski raw/key önkoşulu başlangıç tarihine ayrıldı; doctor'ın mevcut store'u salt okunur açması gerçek kod/test ile hizalandı; araştırma raporundaki "Son durum: Proposed" Accepted/onay sonrası duruma çekildi. Runtime mantığında yeni kusur veya eksik nihai tüketici kontrolü doğrulanmadı.

180 odaklı contract/probe/CI ve 35 TLS/API/CLI kontrolü, ayrı 93 Platform + 7 doctor vakası, Ruff/strict mypy 74 kaynak, 143 belge/6 skill/17 kart ve 155 arşiv geçti. Bu alt kümeler örtüşür; bağımsız toplam test sayısı diye toplanmaz. Ana tam takım sürüyor; temiz kurulum ve yeni seri M5 ölçümleri henüz tamamlanmış değildir. Farklı fresh ajanlarla ikinci tur bu kayıt commit'inden sonra yapılır; kullanıcı hesabı/ağ/probe tekrar kullanılmadı.

### ADR-0022 kabul geçişi — ikinci fresh review turu

cf1d263 üzerinde farklı yeni ajanlar adr22_accept_r2_contract ve adr22_accept_r2_proof nihai kabul geçişini bağımsız inceledi. Tek P3: current.md üst özetinde kalan eski blocked/raw-auth-live ifadesi güncel Accepted kapsamı, P02-0d in_progress/P02-0b draft ve son kaynak/PR/CI durumuna hizalandı; yeniden kontrolde kapandı. Kod/kanıt incelemesinde yeni doğrulanmış bulgu yok. 173 belge/sözleşme odaklı vaka ve ayrı 180 contract/probe/CI + 35 TLS/API/CLI kümesi geçti; örtüşen kümeler toplam diye sayılmaz. 143 belge/6 skill/17 kart ve diff geçti. Gerçek hesap koşusu tekrarlanmadı; yeni M5 ve temiz kurulum kabulü henüz bekler.

Onay/kapsam geçişi iki fresh turuyla kapandı. Son runtime/workflow/test kaynak baytları 92c358a ile aynı; sonraki commit'ler yalnız belge düzeltmesidir. Ana tam takım bu baytlar üzerinde sürüyor. Referans host Apple M5 Max/arm64, macOS 27.0.1 ve internal SSD/APFS olarak yeniden kontrol edildi; benchmark tam takım ve diğer test/build işleri bittikten sonra seri yürütülecek.

## P02-0 son kaynak yerel kabulü

Son runtime/workflow/test kaynağı 92c358a; belge kapanışı 15aa8a1. Bu iki commit arasında src/tests/scripts/workflow/pyproject/lock farkı yoktur. Ana tam takım **3.695 passed, 1 skipped / 595,33 s** ile geçti; tek skip macOS'ta çalışmayan Linux native-counter regresyonudur. Gerçek Windows çalıştırması yapılmadı. Ruff format/lint, strict mypy 74 kaynak, 143 public Markdown/6 skill/17 kart ve diff geçti. Araştırma yürütücülerinin 29 sentetik vakası ayrıca önceki odaklı kabulde geçti; tam ürün takımına dahilmiş gibi sayılmaz.

### Build ve iki temiz runtime kurulumu

15aa8a1 üzerinde uv build sdist'ten wheel üretti. Dağıtım izin listesi ve her artifact için ayrı temiz runtime-only kurulum; repo dışından import origin/basic/NDJSON, gerçek yerel TLS HTTP/stream, cache/execution/jobs smoke kontrolleri geçti. Kurulu Platform senaryosu gerçek public API ve bağımsız kritik alan oracle'ını kullanır; canlı EVREN erişimi değildir.

| Artifact | SHA-256 | Üye |
|---|---|---:|
| Wheel | 692a49fb18bd1f602f8bea4a7ded4470a84158d5daf32ca599a1effb1df890ff | 66 |
| Sdist | ec28052f05b42c10674b1a18de4eea1e198525b107c60c4168c25463f4f15826 | 413 |

[İki kurulum kaydı](evidence.md#p02-0-final-installation) kapalı installation_v2 olarak arşivlendi. Private hazırlık, raw arşiv ve bytecode paket dışındadır; sürümlü araştırma yöntem/test kaynakları sdist'tedir. Bu artifact'ların kimliği 15aa8a1 build'ine aittir; sonraki yalnız belge commit'i için yeni artifact üretildiği iddia edilmez.

### Seri M5 startup ve jobs kabulü

Tam test/build/kurulum işi bittikten sonra, aynı host Apple M5 Max/arm64 + macOS 27.0.1 + CPython 3.11.18 + internal SSD/APFS üzerinde seri çalıştı. Başlamadan önceki süreç görünümünde fseventsd yaklaşık bir çekirdek, GUI/OrbStack arka plan yükü görüldü; kusursuz idle veya fiziksel soğuk cache garantisi verilmez. Başka yoğun test/build işi çalıştırılmadı. Kaynak/kurulum/fixture snapshot'ları önce/sonra eşit; startup adayı ile iki temiz kurulumdaki wheel SHA-256 eşittir. Startup ayrı bc9532c runtime baseline'ıyla aynı-host AB/BA'dır; A/A değildir.

| 30 ayrı süreç p95 | Aday ms | Taban ms | Bütçe ms |
|---|---:|---:|---:|
| help | 23,977 | 24,115 | 500 |
| version | 23,876 | 23,978 | 500 |
| context | 80,854 | 83,219 | 200 |
| cache (1.024 kayıt) | 118,841 | 115,935 | 200 |
| jobs normal/list | 107,846 | — | 200 |
| jobs normal/show | 111,424 | — | 200 |
| jobs dense/list | 151,332 | — | 200 |
| jobs dense/show | 110,782 | — | 200 |

[Startup](evidence.md#p02-0-final-reference-startup) ve [jobs](evidence.md#p02-0-final-reference-jobs) özgün kayıtları saklandı. İlk süreç/ısınma ve nearest-rank yöntemi kanonik standarda bağlıdır; bu tablodaki yuvarlama karar hesabının yerine geçmez. Salt docstring/kaynak geçişi üzerinden performans optimizasyonu iddia edilmez; önceki ölçümler farklı koşulun tarihsel kaydıdır. Ek özet okumasında p95 alan adı ilk denemede yanlış yorumlandı; gerçek ölçüm/validator başarısı değişmedi, warm_p95_ms üzerinden doğru özet alındı. Koşu tekrarlanmadı veya en hızlı sonuç seçilmedi.

158 arşiv/manifest/indeks ve workflow'daki yeni iki current-source M5 verifier geçti. Bu M5 kabulüdür; Linux performansı veya tüm host'larda kesin süre garantisi değildir. CI'da yeni gerçek Linux raw RSS ve üç ortam/altı kurulum ayrı koşacaktır. Canlı hesap 6 GET ve 5 GET koşuları tekrarlanmadı; son kaynakta değişen tüketici satırı yalnız modül açıklamasıdır, gerçek decoder/final-state davranışı aynıdır.

### Kalan kapanış

Platform son kaynak yerel kabulü tamamlandı; P02-0d in_review, ona bağımlı aggregate P02-0b draft ve P02-0 partial kalır. Bu kanıt adımı commit ve iki farklı fresh review turuyla incelenir; sonra tek development PR/üç ortam CI. Kullanıcı PR review/merge yapacaktır; doğrulanmış kimlik/bağ P02-R1 draft ve sonraki veri/çıkarım epikleri bu paketle yapılmış sayılmaz.

### Son yerel kabul — birinci fresh review turu

5bd9107 üzerinde yeni ajanlar p020_final_r1_proof ve p020_final_r1_docs özgün full-suite/build/kurulum ve üç yeni ham kabul kaydını, kaynak/fixture/wheel eşliğini ve aktif ürün belgelerini bağımsız inceledi. Proof kontrolünde yeni bulgu yok; 3.695/1/595,33 s logu, 66/413 üye/SHA, gerçek kurulu TLS/API oracle'ı, bc9532c baseline ve 158 arşiv/current-source verifier sonucu raporla eşleşti. Büyük ham açılımlar genel review bağlamına taşınmadı; yalnız üç hedef kayıt araçla karşılaştırıldı.

Tek P3: capability-matrix C13 hâlâ tüm canlı hizmet adaptörünü sonraki fazda anlatıyordu. Dar LLM/Platform discovery API ve gerçek consumer canlı kabulü mevcut/PR-CI bekler; gerçek execution/ForgeLM ve diğer araç adaptörleri sonraki fazdadır biçiminde düzeltildi. P01 tarihsel teslimi korundu. Belge/ajan/diff kontrolleri geçti; yeni full-suite/build/benchmark veya canlı hesap koşusu yapılmadı. Farklı fresh ajanlarla ikinci kanıt turu bu fix/kayıt commit'inden sonra yapılır.

### Son yerel kabul — ikinci fresh review turu

170a44a üzerinde farklı yeni ajanlar p020_final_r2_proof ve p020_final_r2_docs bütün son yerel kabulü bağımsız inceledi; yeni doğrulanmış bulgu yok. C13 düzeltmesi, yerel kabul ile PR/CI ayrımı, P02-R1/B14 draft takip ve no-authority wire tutarlı. Özgün 3.695/1/595,33 s, iki kurulum SHA/66–413 üye, 61 kurulu runtime dosyasının güncel kaynak eşliği, üç kayıpsız arşiv ve 158/current-source verifier, gerçek bc9532c AB/BA tabanı ve wheel/fixture/p95 eşliği yeniden karşılaştırıldı. 143 belge/6 skill/17 kart ve diff geçti; tam takım/build/benchmark veya canlı hesap koşusu tekrarlanmadı.

Kod ve yerel kabul adımları iki farklı fresh turuyla kapanmıştır. Sonraki işlem tek development PR ve üç ortam CI kabulüdür. P02-0d in_review, aggregate P02-0b draft ve P02-0 partial bu dış teslim koşulu geçilmeden verified yapılmaz. Kullanıcı PR review/merge yetkisini korur; ajan merge yapmayacaktır.

## PR #12 ve metadata kaynaklı CI tekrarının düzeltilmesi

[PR #12](https://github.com/HodeTech/Yorunge/pull/12) b0f485f head'iyle development hedefli açıldı. GitHub connector create çağrısı integration 403 döndürdü; PR oluşmadığı doğrulanıp aynı başlık/gövde mevcut yetkili gh oturumuyla oluşturuldu. Sonar ve branch-policy geçti. [İlk source koşusu 41278581884](https://github.com/HodeTech/Yorunge/actions/runs/41278581884), ardından [41278711872](https://github.com/HodeTech/Yorunge/actions/runs/41278711872) cancelled oldu; başarı olarak sayılmadı. Aynı head için sırasıyla coldtea-pr-lens[bot] ve coderabbitai[bot] metadata düzenlemeleri yeni koşu açmıştı. [Üçüncü koşu](https://github.com/HodeTech/Yorunge/actions/runs/41278900870) aynı eski source head'indedir; yeni bakımın kanıtı değildir.

Neden: core workflow `edited` olayını kaynak değişimiyle aynı concurrency grubunda ele alıp çalışan üç testi iptal ediyordu. Salt edited'i kaldırmak ilk kez başka base'den development'a retarget edilen PR'ı required kontrolsüz bekletebilir. Required job'ı metadata'da skip etmek de skipped check'in başarı sayılması nedeniyle uygun değildir. Mevcut branch/required-check/retarget sözleşmesi korunarak dar CI düzeltmesi yapıldı: yalnız tanımlı başlık/gövde ve base değişimi olmayan edit ayrı metadata grubu; ağır hücreler yok, aggregate adı core-metadata. Source/base değişimi, manual/push ve bilinmeyen edit tam source koşusudur; offline-core üç başarı/explicit startup kanıtı şartını korur. Metadata mode bilinmeyen veya ağır hücre sonucu beklenmedikse audit de reddeder.

Bu aynı güvenlik/kabul koşulunu uygulayan CI hata düzeltmesidir; yeni ürün/otorite kararı veya yeni ADR gerekmez. Git standardı ve gerçek aggregate/config regresyonları birlikte güncellendi; actionlint GitHub expression/job graph'ını doğrular. Yerel testte sınıflandırma string'leri/graph ve gerçek aggregate Python kodu sınanır; GitHub'ın gerçek edited-event semantiği son head üzerinde PR gövdesinin gerekli bakım açıklamasıyla güncellenmesinden sonra ayrıca gözlenecektir. Bu native kabul henüz tamamlanmış değildir.

Workflow/test baytları değiştiği için 15aa8a1 M5 kayıtları bu yeni bakım kaynağının kabulü sayılamaz. Yeni adlar ölçümden önce p02-0-delivery-reference-startup.json ve p02-0-delivery-reference-jobs.json seçildi; eski kayıtlar korunur. Yeni kaynak/iki kurulum/seri M5 ve iki fresh review sonrası aynı PR'a push edilecek; sonra gerçek üç ortam CI. Tam 3.695 ürün takımı önceki aynı runtime üzerinde geçmişti; bu bakım runtime Python davranışını değiştirmez ve yeni CI/metadata testleri ayrıca sınanır. Son current-source CI tamamlanmadan verified iddiası yoktur.

### CI bakımı ve PR belgeleri — birinci fresh review turu

250c7ba üzerinde yeni ajanlar ci_metadata_r1_security ve ci_metadata_r1_tests expression/group/name/guard eşliğini, retarget/unknown-edit ve skipped-required-check sınırını, gerçek aggregate kodunu bağımsız inceledi; doğrulanmış yeni bulgu yok. 81 gate/policy testi, actionlint, Ruff/strict mypy, 143 belge/6 skill/17 kart ve diff geçti. Native GitHub edited kabulü ile yeni M5 henüz tamamlanmış değildir.

PR #12 CodeRabbit incelemesindeki beş küçük belge bulgusu güncel dosyada doğrulanıp minimal düzeltildi: ADR-0021'in son notundaki eski Proposed hükmü tarihsel/forward anlatıma ayrıldı; identity-context modülü ve reference indeksi uygulanmış Platform/LLM gözlemini gösteriyor; hesap hazırlığı negatif kontrolleri normal discovery dışında ayrıca yetkili opsiyonel araştırma olarak belirtiyor; P03-1 yalnız Platform alt kabulü P02-0d'ye bağlandı. Diğer bağımlılıklar ve endpoint/otorite sınırları değişmedi. Yorum içindeki komut/ajan talimatları yürütülmedi. Gerçek kimlik/secret/probe çağrısı yok; tarihsel araştırma ve eski başarısızlıklar korunur. Bu fix/kayıt commit'inden sonra farklı fresh ajanlarla ikinci tur yapılır.

### CI bakımı ve PR belgeleri — ikinci fresh review turu

fba5c51 üzerinde farklı yeni ajanlar ci_metadata_r2_security ve ci_metadata_r2_docs_tests kaynak/metadata predicate eşliğini, required-check adının ayrılmasını, fail-closed gerçek gate kodunu ve beş belge düzeltmesini bağımsız inceledi; yeni doğrulanmış bulgu yok. 81 test/actionlint, 143 belge/6 skill/17 kart ve diff geçti. Native GitHub metadata kabulü ve yeni source-bound M5 ölçümleri hâlâ sonraki kabul adımıdır; bu review canlı semantiği geçmiş saymaz.

### İlk PR source koşusunun tarihsel gerçek CI kanıtı

[41278900870](https://github.com/HodeTech/Yorunge/actions/runs/41278900870) b0f485f head / 29ec2562b985815184e1f15638178ef474a7710d test merge kaynağında üç ortam ve aggregate ile başarılı tamamlandı. Linux 3.11 **3.696 passed / 586,98 s**, Linux 3.14 **3.696 passed / 579,40 s**, macOS 3.11 **3.695 passed, 1 Linux-only skip / 618,04 s**. Üç ortamın altı temiz kurulum kaydı ve gerçek Linux raw ölçümü kalıcı arşive alındı; ZIP SHA'ları API artifact digest'iyle eşleştirildi. Kaynak PR head'i ile test merge SHA ayrı kaydedildi. Bu, henüz push edilmemiş CI bakımının kanıtı değildir.

[Linux 3.11](evidence.md#p02-0-pr12-first-linux311-installation), [Linux 3.14](evidence.md#p02-0-pr12-first-linux314-installation) ve [macOS](evidence.md#p02-0-pr12-first-macos311-installation) installation_v2 wrapper'ları özgün ci-environment/JSONL ve ZIP hash'lerini taşır. [Linux startup özgün başarısız ölçümü](evidence.md#p02-0-pr12-first-linux-startup) ve [diagnostic receipt](evidence.md#p02-0-pr12-first-linux-receipt) baytları değişmedi: AMD EPYC 7763, disk unknown; candidate/cache p95 **221,490 ms**, baseline **216,552 ms**; ikisi de 200 ms üstünde. ADR-0019 politikasıyla ci_classification_accepted=true, diagnostic_budget_exceeded kaldı; Linux performans kabulü geçti diye yeniden etiketlenmedi. M5 bağlayıcı hedefi ayrı yeşildir; kullanıcı PR review'sinde bu Linux tanısını ayrıca görecektir, insan incelemesi ajan tarafından yapılmış sayılmaz.

[Gerçek Linux raw](evidence.md#p02-0-pr12-first-linux-stream) 16/256/1.024 MiB, byte/SHA, native RSS ve çapraz boyut farkı kapılarını geçti; ek RSS aralık üst sınırı en çok 655.360 byte, çapraz boyut span aynı değerdir. Eski iki iptal ve başarısız Linux tanısı saklandı. Bu eklerle 164 arşiv doğrulandı. Son bakım head'inin yeni M5/native edited ve gerçek CI kabulü tamamlanmadan kartlar verified yapılmaz.

## CI bakımının son kaynak yerel kanıtı

CI/test kaynağı 250c7ba/fba5c51; belge/ilk CI kanıtı bfd43a8. Aralarındaki product runtime Python baytları aynıdır. Yeni CI davranışı 81 gate/policy regresyonu ve actionlint ile iki fresh turda geçti. Önceki tam 3.695 ürün takımı ve ilk PR'daki üç tam takım aynı runtime davranışına aittir; yeni on gate vakası bu eski sayılara eklenmiş gibi sunulmaz. Son bakım head'inde tam takımın gerçek CI tekrarını bekliyoruz; yerelde ilgisiz ürün takımını tekrar koşmak yerine değişen CI/metadata sınırı sınandı.

fba5c51 build'i yeniden sdist'ten wheel üretti; iki ayrı temiz runtime-only kurulum origin/basic/NDJSON/gerçek TLS-HTTP-stream/Platform oracle/cache/execution/jobs kontrollerini geçti. Wheel **66** üye / **fb6e2486e02d02390a137bd5e59dbeb48408f32de6ec1c2166a879a077e4afb0**; sdist **413** üye / **1ad746145267467cfa10ce73e360027c38a1c207f2c85b9d87f65afd2b32f367**. Önceki wheel'den değişen üyeler yalnız README'yi taşıyan METADATA ve RECORD; tüm runtime üyeleri bayt eşittir. [İki kurulum](evidence.md#p02-0-delivery-installation) özgün kayıtla saklanır; gerçek hesap dosyası/raw/bytecode paket dışında kalır.

Yeni [startup](evidence.md#p02-0-delivery-reference-startup) ve [jobs](evidence.md#p02-0-delivery-reference-jobs) bfd43a8 source snapshot'ında test/build işi bittikten sonra seri çalıştı; Apple M5 Max/arm64/macOS 27.0.1/CPython 3.11.18/internal SSD-APFS aynı referans host'tur. Startup bc9532c ile gerçek AB/BA; aday wheel yeni iki kurulumdaki hash ile eşittir. Kaynak/kurulum/fixture önce/sonra değişmedi. OS cache boşaltma/ideal idle/katı fiziksel süre veya yeni runtime optimizasyonu iddia edilmez.

| Her biri 30 süreç p95 | Aday ms | Taban ms | Bütçe ms |
|---|---:|---:|---:|
| help | 23,530 | 22,874 | 500 |
| version | 22,623 | 23,233 | 500 |
| context | 75,352 | 74,191 | 200 |
| cache | 117,598 | 115,407 | 200 |
| jobs normal/list | 122,620 | — | 200 |
| jobs normal/show | 100,907 | — | 200 |
| jobs dense/list | 142,193 | — | 200 |
| jobs dense/show | 107,671 | — | 200 |

167 arşiv/manifest/indeks ve yeni current-source startup/jobs verifier geçti. Eski 15aa8a1 M5 kabulü korunur; yeni workflow/test hash'leri onunla geçirilmedi. Bu kayıt commit'i ve kanıt review sonrası aynı PR'a aktarılacak; native edited-event/check-name ve son source CI henüz bekliyor. Public source kontrolü veya required check metadata audit'iyle yeşile çevrilmeyecek.

### Bakım kanıtı — birinci fresh review turu

6a74d36 üstünde yeni ajanlar delivery_proof_r1 ve delivery_docs_r1 yeni üç yerel kayıtla ilk CI'ın altı kaydını, kaynak/hash/p95 ve aktif üst özetleri bağımsız inceledi. Proof kontrolünde yeni bulgu yok; dokuz özgün JSON arşivle bayt eşit, 167/current-source verifier ve iki kurulum/runtime/AB-BA eşliği doğru. Tek P3: bazı üst özetler önceki aynı-runtime 3.695 tam takımı yeni CI guard kaynağının tam takımı gibi anlatıyor ve current eski kabul bölümüne bağlanıyordu. Bunlar önceki 3.695 + yeni 81 guard/iki kurulum/M5 ile native/current CI bekleme ayrımına çekildi; bağlantı güncel bakım kanıtına yönlendirildi. Belge/ajan/diff geçti; full-suite/benchmark/canlı hesap tekrarlanmadı. İkinci tur farklı fresh ajanlarla bu fix/kayıt commit'inden sonra yapılır.

### Bakım kanıtı — ikinci fresh review turu

57b924a üstünde farklı yeni ajanlar delivery_proof_r2 ve delivery_docs_r2 bakımın bütün kanıtını ve düzeltilen üst özetleri bağımsız inceledi; yeni doğrulanmış bulgu yok. Dokuz özgün kayıt/167 arşiv/iki current-source verifier, artifact SHA ve 66/413 üye, 61 runtime dosyası, METADATA-RECORD farkı ve gerçek bc9532c AB/BA tabanı bağımsız karşılaştırıldı. İlk CI wrapper/başarısız Linux tanısı/raw RSS sınırı tutarlı. 143 belge/6 skill/17 kart ve diff geçti; hesap/probe/full-suite/benchmark tekrar edilmedi.

CI bakımı ve yenilenen yerel kabul iki farklı fresh turuyla kapandı. Bundan sonra mevcut PR #12 güncellenir; gerekli PR gövde düzenlemesi native metadata concurrency/check-name testi olur. Ağır source koşusunun devamı, metadata koşusunda core-metadata/üç skipped hücre ve required offline-core üretilmemesi gözlenecek. Son bakım head'inin üç ortam source CI'ı geçmeden verified kaydı yoktur.

## PR #12 son kaynak CI ve paket kapanışı

Source head **e475992d97c61e5288e92d414d8c0f6f8ee00a5a**, test merge **ba45a2e8b019632d0b48a9af5034b93c9ceb1012** için [CI 41280791049](https://github.com/HodeTech/Yorunge/actions/runs/41280791049) üç ortam ve gerçek `offline-core` aggregate ile başarılıdır. Linux 3.11 **3.706 passed / 603,17 s**, Linux 3.14 **3.706 passed / 433,48 s**, macOS 3.11 **3.705 passed, 1 Linux-only skip / 618,11 s**. Yeni on CI guard vakası bu son tam takımlara dahildir. Statik/belge/ajan, üç ortamın altı temiz kurulumu, iki current-source M5 verifier ve gerçek Linux raw geçti; SonarCloud ve branch-policy başarılı. Sourcery review skipped kaldı; başarılı sayılmadı. Beş doğrulanmış CodeRabbit belge bulgusu yayınlanan fix'lerle ve iki fresh turla kapatıldı.

### Native metadata kabulü

PR açıklaması güncellenirken mevcut PR Lens ve CodeRabbit bölümleri aynen korundu; onların URL parametreleri loga/repoya yazılmadı. [Elle gövde düzenlemesi 41280870597](https://github.com/HodeTech/Yorunge/actions/runs/41280870597) ve [CodeRabbit düzenlemesi 41281037868](https://github.com/HodeTech/Yorunge/actions/runs/41281037868) aynı e475992 head'inde `core-metadata=success`, üç ağır hücre `skipped` ve **sıfır offline-core job/check adı** üretti. Source 41280791049 bu iki audit sırasında iptal olmadı, üç tam takımı bitirdi ve kendi offline-core başarısını üretti. Audit tamamlanıp source hâlâ beklerken PR mergeStateStatus BLOCKED idi; required bağlayıcı source başarısı henüz yoktu. GitHub özetindeki son metadata hücreleri SKIPPED görünebilir; asıl üç tam takımın sonucu source run ID'sinden ayrı doğrulandı.

Native kabul için gerçek protected-base retarget/advance deneyi yapılmadı; bu yolların predicate/config ve fail-closed aggregate sınırı 81 regresyon ve actionlint ile doğrulandı. Repository korumaları salt okunur kontrol edildi: development strict=true, Master strict=false; ikisinde required `offline-core` ve `branch-policy`, app_id 15368. İzin/koruma ayarı değiştirilmedi; token contents:read kalır.

### Son CI kanıtının kalıcı saklanması

[Linux 3.11](evidence.md#p02-0-pr12-delivery-linux311-installation), [Linux 3.14](evidence.md#p02-0-pr12-delivery-linux314-installation) ve [macOS](evidence.md#p02-0-pr12-delivery-macos311-installation) kurulum wrapper'ları özgün environment/JSONL ve artifact ZIP SHA'larına bağlıdır; altı gerçek kurulum geçti. [Linux startup](evidence.md#p02-0-pr12-delivery-linux-startup), [receipt](evidence.md#p02-0-pr12-delivery-linux-receipt) ve [raw](evidence.md#p02-0-pr12-delivery-linux-stream) özgün baytları korunur. Bu eklerle **173 arşiv** doğrulandı.

Son Linux cache p95 aday **225,741 ms**, taban **226,712 ms**; her ikisi de 200 ms üstündedir. Diagnostic_budget_exceeded başarısız ölçüm olarak kaldı; ADR-0019 CI sınıflandırması kabul edildi diye Linux performans hedefi geçmiş sayılmaz. Kullanıcı PR review'sinde bu tanıyı ayrıca değerlendirir; ajan insan onayı varmış gibi kaydetmez. Son M5 bağlayıcı cache **117,598 ms**, dört jobs p95 değeri **122,620 / 100,907 / 142,193 / 107,671 ms** ile kapıları geçmiştir. Native Linux raw 16/256/1.024 MiB ve RSS/span kapılarını geçti; ek RSS üst sınırı ve çapraz boyut span en çok **655.360 byte**. İlk iki iptal, önceki Linux aşımı ve bütün geçmiş kaynak kayıtları silinmedi veya seçilerek başarıya çevrilmedi.

### Yeni CI yorumunun doğrulanması

CodeRabbit'in son ek yorumu, base ilerledikten sonraki metadata edit'inin test merge SHA'sında offline-core bırakmayacağını öne sürdü. Güncel API'de source offline-core ve iki metadata audit'inin check_run.head_sha alanı e475992 PR head'idir; checkout edilen ba45a2e test merge SHA'sında **check-runs=[] ve status total_count=0**. [GitHub kuralı](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks#conflicts-between-head-commit-and-test-merge-commit) bu durumda güncel head kontrollerinin değerlendirildiğini açıklar. Dolayısıyla checkout SHA'sı ile required check bağlı SHA eşit varsayılarak verilen bulgu mevcut repo için doğrulanmadı. Bağımsız ci_metadata_retrigger_review da aynı disposition'a ulaştı. Workflow geri çevrilmedi, checks:read izni eklenmedi. Gerçek base-advance deneyi yapılmadığı sınırı korunur; development strict sync ve Master'ın ADR-0009 loose politikası değişmez. Bu gerekçe konuşma kapanışı için kayıttadır.

### Teslim sınırı

P02-0a/0b/0c/0d ve dar **P02-0 çalışma dalı kabulü verified**: uygulama, anlamlı test, iki fresh review döngüleri, gerçek consumer canlı kabulleri, kaynak bağlı yerel kanıt ve son source CI tamamlandı. Bu, development merge veya paket yayını değildir; PR #12 kullanıcı incelemesine açıktır ve ajan merge yapmaz. Auth/kimlik/izin public unknown/unverified/null kalır; özgün doğrulanmış kimlik/bağ P02-R1/B14 draft'tır. P02-1–7 uygulanmış sayılmaz; sıradaki epik P02-1'dir. Bu kapanışın yalnız belge/arşiv commit'i kaynak/workflow/test baytlarını değiştirmez; son head'in zorunlu CI'ı ayrıca izlenecektir.

Son yalnız belge/arşiv commit’inin ve kullanıcının olası merge’ünün ek Linux raw/receipt koşuları için kalıcı saklama takibi açıktır: mevcut veya sonraki yetkili dalda, sonraki kabul/merge önerisinden önce ve 90 günlük artifact süresi dolmadan özgün baytlarla arşivlenir. Burada e475992 son incelenen kaynak CI’ının altı kaydı kalıcıdır; sonraki koşu şimdiden arşivlenmiş sayılmaz.

Son kapanış fact-check’inde delivery_docs_r2 ve delivery_proof_r2 belge durumlarını ve altı yeni kaydın özgün artifact/ZIP/environment/JSONL/hash eşliğini ayrıca kontrol etti. Bu, önceki iki fresh turun yeniden sayılması değildir. Modüldeki eski PR/CI bekleme ifadesi ve aktif özetler düzeltildi; açık bulgu kalmadı. 143 belge, 6 skill/17 kart, 173 arşiv, iki current-source M5 verifier ve diff geçti. Tam takım/benchmark/canlı hesap tekrar edilmedi; test sayı/süreleri ana ajanın GitHub job-log doğrulamasından, metadata davranışı ayrı native kabulden gelir.

## PR #12 kullanıcı review düzeltmeleri

5583ca0 / bc9532c incelemesindeki dört bulgu güncel kaynakta doğrulandı. Yerel profil/account/project tercihleri, override ile gizlenen profil projesi dahil, ortak exchange içinde ilk GET’ten önce seçili credential’ın mevcut literal kuralıyla denetlenir; eşleşmede değer taşımayan invalid_request/exit 2 döner. Böylece kısa sır endpoint öneki eklenmeden kontrol edilir. LLM/Platform DTO’ları yayımdan önce mevcut typed literal denetiminden ayrıca geçer. Kısa sırların ilgisiz alt dizeleri veya sabit protokol alanları için mutlak alt-dize yasağı getirilmedi; mevcut ADR sınırı değişmedi, yeni karar gerekmedi.

Hesap hazırlığı dolu account/project tercihlerini config profiline de yazar; scope.json yalnız araştırma girdisidir. Eski hazırlık için açık profil/CLI geçişi ve credential dosyasından yalnız seçili pilot env adını çocuk sürece aktaran çalıştırılabilir örnek eklendi. Parent env değişmez; key shell argümanına/çıktıya girmez. Yeni test gerçek doküman bloklarını sentetik gizli girişlerle çalıştırır; yalnız test hedef/CA kompozisyonunu değiştirerek gerçek TLS/CLI sonucunda tercih, seçili proje/detail, hizmet/env ayrımı ve hata davranışını sınar. Görev indeksindeki “Aktif P02-0” ifadesi tamamlanmış paket ve sıradaki P02-1 yönlendirmesine çevrildi.

### 5583ca0 kapanış CI saklama takibi

[41282647619](https://github.com/HodeTech/Yorunge/actions/runs/41282647619) source 5583ca0 / checkout **5e09657d9cf152258dc2fb085a97ea444f3b983e** için üç ortam/aggregate başarılıdır. Linux 3.11 **3.706 / 399,59 s**, Linux 3.14 **3.706 / 591,39 s**, macOS **3.705 + 1 platform skip / 536,43 s**. [Linux 3.11](evidence.md#p02-0-pr12-closure-linux311-installation), [Linux 3.14](evidence.md#p02-0-pr12-closure-linux314-installation), [macOS](evidence.md#p02-0-pr12-closure-macos311-installation) altı temiz kurulum ve özgün environment/JSONL/ZIP hash’lerini taşır. [Startup](evidence.md#p02-0-pr12-closure-linux-startup), [receipt](evidence.md#p02-0-pr12-closure-linux-receipt) ve [raw](evidence.md#p02-0-pr12-closure-linux-stream) özgün baytlarıyla saklandı; toplam **179 arşiv** doğrulandı. Önceki son-belge CI saklama takibi bu altı kayıtla kapandı.

Bu ayrı koşuda Linux cache p95 aday/taban **144,363 / 142,878 ms** ile geçti. Önceki **225,741 / 226,712 ms** başarısız tanısı değişmedi; yeni başarı onu geriye dönük olarak geçirmiş saymaz. Yeni ürün fix’i eski kaynak performans kanıtıyla kabul edilmez: workflow/test yeni review-reference adlarını seçti; iki fresh review sonrası son kaynak tam takım, iki temiz kurulum ve seri M5 startup/jobs yenilenecek. Yeni gerçek EVREN çağrısı yapılmadı; önceki canlı davranış yeni kod çalıştırılmış gibi sunulmaz. PR kullanıcı review/merge ve Master/release ayrı kalır.

İlk düzeltme doğrulaması: 275 odaklı discovery/public CLI/rehber/response JSON/CI-matrix testi geçti (83,04 s). Ruff format/lint, strict mypy (74 kaynak), actionlint, 143 belge/6 skill/17 kart, 179 arşiv ve diff geçti. İlk test yazımında text/JSON hata zarfı beklentisi ve rehber TLS fixture’ının eksik doc_path alanı düzeltildi; başarısız deneme son başarı diye sunulmadı. Son tam takım/build/M5 ve iki fresh review henüz bu adımın sonraki kapılarıdır.

### Kullanıcı fix’i — birinci fresh review

0a89b81 üstünde pr12_fix_r1_security ve pr12_fix_r1_ux_evidence bağımsız inceledi. Kullanıcı bulguları kapandı; iki ilişkili P2 doğrulandı: rehberin set-project prose komutu positional argüman gerektiriyor; hedef literal kontrolü capture dönüşünde yapıldığında registry hedefi daha önce commit edebiliyor. Komut positional biçime düzeltildi ve gerçek prose/CLI/config migration testi eklendi. Aynı saf yerel denetim capture içinde credential çözümlendikten hemen sonra, binding yazısından önce uygulanır; exchange kapısı alternatif state portları için korunur. İki hizmet için hedef canary’sinin DB’ye girmediği, binding satırı oluşmadığı ve ağ yapılmadığı sınanır; bütün yerel alan negatiflerinde de sıfır binding doğrulanır.

179 arşiv ve üç ZIP/altı özgün kayıt eşliği UX/kanıt ajanıyla ayrıca doğrulandı. R1 fix doğrulaması: iki hedef/DB regresyonu ve dört rehber yolculuğu geçti; Ruff/mypy/belge/ajan/diff temiz. Önceki 275 test R1 öncesi kaynağa aittir; son tam takım/iki kurulum/M5 ve ikinci fresh tur sonraki adımdır. Yeni EVREN veya koruma/izin ayarı değişikliği yoktur.

### Kullanıcı fix’i — ikinci fresh review

3aa5903 üstünde farklı fresh ajanlar pr12_fix_r2_security ve pr12_fix_r2_ux_evidence bağımsız inceledi; yeni doğrulanmış bulgu yok. Security dört hedef/DB ve kısa-sır pozitif vakasını, UX dört rehber/gerçek prose komut yolculuğunu çalıştırdı. Registry öncesi ve alternatif-port exchange denetimi, nihai DTO literal sınırı, final credential/clock/deadline ve cleanup korundu. 143 belge, 6 skill/17 kart, 179 arşiv/diff geçti. Son kaynak 3aa5903 build’i 66 üyeli wheel ve 414 üyeli sdist’i iki ayrı temiz runtime’a kurup bütün smoke kontrollerini geçti; tam takım ve seri M5 bu kaydın ardından tamamlanır.

Review’deki BLOCKED/onay yorumu ayrı doğrulandı: 5583ca0 için required approving review count=0, code-owner/last-push onayı kapalı, açık konuşma yok ve required check’ler başarılıydı; reviewDecision boştu. Bu nedenle yalnız review/approval eksikliği nedenini bu API verileriyle doğrulayamadık. Koruma, izin veya review ayarı değiştirilmedi; son PR head’i ve kapıları ayrıca izlenir.

## Kullanıcı review düzeltmelerinin son kaynak kabulü

Ürün/test/workflow kaynağı **3aa5903**, yalnız review kaydı ekleyen snapshot **042652c**; runtime/test/workflow baytları aynıdır. Kullanıcının dört bulgusu ve R1’in iki ilişkili bulgusu giderildi, farklı fresh R2 ajanlarında yeni bulgu yok. Tam yerel takım **3.785 passed, 1 Linux native-counter skip / 661,13 s**; Ruff format/lint (179 dosya), strict mypy (74 kaynak), actionlint, 143 belge/6 skill/17 kart ve diff geçti. Önceki kaynak CI başarıları bu yeni ürün kodunun testi sayılmadı.

[İki ayrı temiz kurulum](evidence.md#p02-0-review-installation) sdist’ten wheel build’i ve gerçek runtime-only origin/basic/NDJSON/TLS-HTTP/stream/Platform kritik oracle/cache/execution/jobs kontrollerini geçti. Wheel **66 üye / 3f843c8500d59536dce132f6a40fd026c92447c3f468909d5e85f65fcb41b230**; sdist **414 üye / 8cab13a1f5fa2acc315f0f9f69a531ea4928cbbfbc0182d127c6e689633202d7**. Eklenen üye rehberin gerçek yolculuk testidir; özel hazırlık ve raw arşivler paket dışında kalır.

Yeni [startup](evidence.md#p02-0-review-reference-startup) ve [jobs](evidence.md#p02-0-review-reference-jobs) referansları 042652c source snapshot’ında, test/build bittikten sonra seri üretildi: Apple M5 Max/arm64/macOS 27.0.1/CPython 3.11.18/internal SSD-APFS. Gerçek ayrı bc9532c runtime tabanıyla AB/BA; aday wheel yukarıdaki temiz kurulum hash’iyle eşit. Kaynak/kurulum/fixture before-after değişmedi. Bu fiziksel idle/cache-empty veya Linux için süre garantisi değildir.

| 30 süreç p95 | Aday ms | Taban ms | Bütçe ms |
|---|---:|---:|---:|
| help | 23,412 | 23,530 | 500 |
| version | 22,405 | 21,815 | 500 |
| context | 74,727 | 72,701 | 200 |
| cache | 119,788 | 113,829 | 200 |
| jobs normal/list | 103,356 | — | 200 |
| jobs normal/show | 100,805 | — | 200 |
| jobs dense/list | 150,534 | — | 200 |
| jobs dense/show | 101,926 | — | 200 |

**182 arşiv**, iki güncel source-bound M5 verifier ve indeks/manifest geçti. Önceki başarısız Linux kaydı korunur; 5583ca0 ek CI saklama takibi yukarıdaki altı kayıtla kapandı. Yeni gerçek hesap çağrısı yapılmadı; mevcut canlı kabul hedef/decoder davranışının önceki kaydıdır, son fix canlıda tekrar denenmiş sayılmaz. Yeni kod için gerçek TLS/SQLite/subprocess ve installed Platform oracle’ı kullanıldı. Bu yerel kabul, son PR head’inin üç ortam CI’ından ayrıdır; PR #12 güncel head kontrolleri izlenir. Kullanıcı merge, Master/release ve P02-1 kapsamı değişmedi.

Kapanış fact-check’inde pr12_fix_r2_ux_evidence üç yeni dist/gzip kaydının bayt eşliğini, iki temiz kurulum/hash/61 runtime dosyasını, gerçek bc9532c tabanını ve 042652c before/after kaynak/kurulum/fixture bağını bağımsız doğruladı; yeni provenance bulgusu yok. Bu kontrol önceki iki fresh turun yeniden sayılması değildir.

## Sonar ve native merge kapısı takibi

Kullanıcı yeni Sonar listesini ve metadata suite 41305658285’in skipped hücreleriyle required offline-core Expected yüzünden merge edemediğini bildirdi. Önceki yalnız API tabanlı kabul/disposition yeterli değildi: c0c9673 source 41305352805 üç hücre/aggregate SUCCESS, doğru head/app15368/PR12 ve GraphQL isRequired=true iken, yenilenmiş gerçek GitHub merge kutusu **4 skipped / 1 expected / 4 successful**, required offline-core Expected ve disabled merge gösterdi; mergeStateStatus BLOCKED sürdü. Review onayı değil required status beklemesi görünüyordu. GitHub’ın iç seçim algoritması kesin saptanmadı; son suite’te dinamik aggregate adıyla required context’in olmaması gözlemle uyumlu açıklamadır. Önceki “API success yeterli” sonucu bu native kanıtla geçersiz kaldı; tarihsel kayıt silinmedi.

Konservatif düzeltme: dinamik aggregate adı, metadata-only hücre skip’leri ve metadata audit başarı dalı kaldırıldı. `edited` dahil her uygun koşu üç gerçek hücre ve sabit offline-core üretir; tüm hücre başarısı ve mevcut startup çıktıları zorunlu kalır. Source/metadata concurrency ayrımı korunur; gövde edit’i kaynak koşusunu iptal etmez. Daha fazla CI maliyeti açıkça kabul edilen uygulama karşılığıdır; fake-green, status yazma/dispatch fallback, ek token izni veya branch-protection bypass yoktur. Yeni native kabul source ve body-edit koşularından sonra gerçek merge kutusunu da içerecek; henüz yapılmış sayılmaz.

### Sonar bulgularının ayrımı

Aktif ürün kodunda Platform raw anahtar muafiyetleri kapalı endpoint/path tablosuna taşındı; tam raw-tree literal dolaşımı küçük yardımcıyla ayrıldı. DTO selection/order/time doğrulaması küçük yöntemlere bölündü; public alan/state/reason/null veya güvenlik kuralı değişmedi. Nested seçim ifadesi açık yerel state adımına ayrıldı. Normal testlerde serialization, secret/reader/state nesnesi, deadline ve compile hazırlığı raises dışına taşındı; assertion yalnız hedef çağrıyı kapsar. Me success testi doğrudan identity’nin zorunluluk kontrolünü sınar; hazırlık parser’ının hatası testi geçiremez.

Beş bakım uyarısı **değişmez tarihsel snapshot** üzerindedir; kaynak/receipt hash’lerini düzeltme adıyla değiştirmek kanıtı bozardı. Sonar hesabında mevcut GitHub SSO ile oturum yenilendi; yalnız aşağıdaki beş issue gerekçesi ve kaynak hash’leriyle **Accepted** yapıldı. Yanlış pozitif veya güvenlik bulgusu olarak işaretlenmedi; genel kaynak/kalite dışlaması eklenmedi. Uygulama sonrası açık liste 30’dan **25**’e indi; aktif kod/test uyarıları yeni analizde fix olarak kapanacaktır.

| Sonar issue | Değişmez kaynak | Disposition |
|---|---|---|
| AaGVqwxf5xr-Pq-FFthq | platform-20261101/account_probe.py; auth/me sabiti | Accepted: receipt kaynak baytları korunur |
| AaGVqwxf5xr-Pq-FFths | platform-20261101/account_probe.py; complexity 41 | Accepted: receipt kaynak baytları korunur |
| AaGVqwxk5xr-Pq-FFthu | platform-project-20261101/project_probe.py; complexity 45 | Accepted: seçili-proje receipt kaynağı korunur |
| AaGVqwxi5xr-Pq-FFtht | platform-20261101/test_probe.py; raises hazırlığı | Accepted: arşiv test snapshot’ı korunur |
| AaGVqwxf5xr-Pq-FFthr | platform-20261101/account_probe.py; set comprehension | Accepted: receipt kaynak baytları korunur |

Hash’ler account **a4e91a029e6e280896403fe8e5918b308415a86c02f3258896b4630b5b517a4c**, test **ab6e47a303c588931be024093c0adbec314b92aa4ddc648c14f8d0bed7a3ac13**, project **9ffc1787901f02ad9a823f6950953f994dedd0615c956169846ead2e6449e27b** olarak aynıdır. Bunlar yeniden çalıştırılmış canlı deneyi veya yeni refaktör edilmiş probe’u temsil etmez. [Sonar issue değerlendirme anlamı](https://docs.sonarsource.com/sonarqube-cloud/managing-your-projects/issues/editing); kanonik snapshot gerekçeleri kendi README’lerindedir.

### c0c9673 source CI kalıcı kanıtı

[41305352805](https://github.com/HodeTech/Yorunge/actions/runs/41305352805), head c0c9673 / checkout **31966204415e124e53cf27aa4b23340a8aad590c**: Linux 3.11 **3.786 / 637,43 s**, Linux 3.14 **3.786 / 475,95 s**, macOS **3.785 + 1 skip / 642,26 s**; üç hücre ve offline-core başarılı. [Linux 3.11](evidence.md#p02-0-pr12-user-review-linux311-installation), [Linux 3.14](evidence.md#p02-0-pr12-user-review-linux314-installation) ve [macOS](evidence.md#p02-0-pr12-user-review-macos311-installation) altı temiz kurulum/ZIP/environment/JSONL bağını taşır. [Startup](evidence.md#p02-0-pr12-user-review-linux-startup), [receipt](evidence.md#p02-0-pr12-user-review-linux-receipt), [raw](evidence.md#p02-0-pr12-user-review-linux-stream) özgün baytları korur; **188 arşiv** doğrulandı. Linux cache aday/taban **218,737 / 217,902 ms** ile başarısız tanıdır; M5 ayrı geçti. Gerçek raw ek RSS üst sınırı en çok **786.432 byte**, çapraz boyut span üst sınırı **655.360 byte**. Bu source CI’ın saklama takibi kapandı; bu başarı yeni Sonar/CI refaktörünün veya native merge kutusunun kabulü değildir.

İlk Sonar/CI düzeltme doğrulaması: 195 ilgili DTO/raw/LLM-state/rehber testi ve 60 gerçek gate/config testi geçti; Ruff format/lint, strict mypy, actionlint, belge/ajan/diff ve 188 arşiv temiz. İlgili normal testlerde raises gövdesinde birden çok çağrı kalmadığı AST ile ayrıca kontrol edildi. Bu kaynak için fresh review, build ve yeni source-bound M5 sonraki kabul adımlarıdır; eski ölçüm yeni refaktörü geçirmez.

### Sonar ve CI — birinci fresh review

08c846b üstünde yeni pr12_sonar_r1_code ve pr12_sonar_r1_ci bağımsız inceledi; yeni kod/CI kusuru yok. Raw muafiyet tablosu ve DTO helper’ları önceki güvenlik/wire invariants ile eşdeğer; 144 contract ve 60 gate testi ayrıca geçti. Tek P3 c0c9673 raw raporunda ek RSS maksimumu ile çapraz boyut span’ının karıştırılmasıydı; 786.432 ve 655.360 byte ayrı yazıldı. Actionlint/docs/skill/188archive ve üç değişmez probe hash’i doğrulandı. Son native merge kutusu henüz kabul sayılmadı; farklı fresh ikinci tur, son kaynak M5 ve GitHub source/body-edit gerçek koşuları izlenecek.
