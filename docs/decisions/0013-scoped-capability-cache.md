# ADR-0013: Kapsamlı capability cache, kanıt ve tazelik

**Durum:** Proposed — kullanıcı onayı bekliyor; ürün uygulaması başlamadı. **Tarih:** 2026-10-27. **İş:** P01-3a. [Ön inceleme](../research/p01-3-readiness-review.md), [teslim planı](../roadmap/p01-3-delivery-plan.md).

## Bağlam

[ADR-0005](0005-capabilities-and-contracts.md) dört destek durumunu ve kapsam/kanıt/zaman bağını kabul eder; cache yenileme ve eski kanıt davranışını açık bırakır. P01-2 artık kalıcı credential kimliği/nesli sağlar. Bu gözlem uzak yetki kanıtı değildir. Bugünkü `Scope`, `Capability` ve `Plan` yalnız offline v1 alt kümesini kabul eder; bunları genişletmek eski dosya ve digest anlamını değiştirebilir.

Bu öneri SQLite, HMAC, hedef normalleştirme veya dosya dayanıklılığı seçimini yeniden açmaz. [ADR-0011](0011-state-foundation-and-migrations.md), [ADR-0012](0012-credential-identity-and-change-detection.md) ve [binding v1](../reference/credential-binding-v1.md) geçerlidir.

## Önerilen karar

### Ayrı kayıt ve tam kapsam

Yeni `CapabilityRecord` biçimi `schema_version=2` olur; mevcut offline v1 modelleri/çıktısı/digest'i değişmez. Yeni kayıtta `capability_id`, `task`, `scope`, dört durumlu `support`, sınırlı reason/message, tipli constraints, kanıtlar, `checked_at` ve `expires_at` bulunur. Bilinmeyen alan/sürüm, duplicate JSON key, NaN/Infinity ve yanlış tür reddedilir.

Yeni scope şu bağların tamamını taşır:

| Bağ | Anlam |
|---|---|
| `store_id`, `identity_epoch`, `clock_generation` | Yerel store, etkin kimlik alanı ve kalıcı saat geçersizleştirme nesli; local-only kayıtlar da bağlıdır |
| Hizmet/hedef | `service_id`, `service_origin`, `api_base_path`; uzak hedef binding v1 ile karşılaştırılır |
| Hesap/proje | Seçilen `account_id`, `project_id`; seçim tek başına doğrulanmış uzak kimlik değildir |
| Credential | Opak `credential_id`, pozitif `credential_revision`; referans adı, tag veya sır yoktur |
| `authorization_scope` | Doğrulanmış global izinler ve kaynak başına izin kayıtları; bilinmiyorsa null |
| Model | Kaynak/kimlik, seçilmiş revision ve varsa doğrulanmış içerik digest'i; bilinmeyen bağ null |
| Araç | Kimlik, doğrulanmış sürüm, executable ve environment digest'leri; yoksa null |
| Execution | Backend, doğrulanmış runtime kimliği/sürümü; bilinmeyen bağ null |

Null **wildcard değildir**; yalnız aynı null alanla eşleşir ve doğrulama yerine geçmez. İzin ve kaynak listeleri sınırlı, sıralı ve tekrarsızdır; kaynak kaydı namespace/type/id ile kendi izinlerini birlikte taşır. Boş doğrulanmış izin kümesi ile bilinmeyen izin ayrıdır. Gerekli olmayan bağ null olabilir; görev için gerekli fakat bilinmeyen bağ execution desteğini engeller. Adapter hangi bağların gerekli olduğunu kendi tipli görev sözleşmesinde bildirir; caller bu gereksinimleri azaltamaz.

Cache anahtarı `capability_id`, `task` ve scope'un **tamamının** kanonik JSON baytlarının SHA-256'sıdır. Kodlama `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=True`, `allow_nan=False`, UTF-8; BOM/newline yoktur. Kayıtlı tam anahtar baytları da okunurken karşılaştırılır; digest tek başına eşitlik veya güven kanıtı değildir. Profil adı, env adı veya ham secret/hash anahtar değildir. Kaynak/politika sürümü değişmiş kayıt yeni kararın yerine kullanılamaz.

### Kanıtın yetkisi

Kanıt türleri `local_policy`, `documentation`, `synthetic_test`, `live_account`, `not_verified` olarak ayrılır; her kanıt producer kimliği/sürümü ve sınırlı provenance taşır. Genel şema/kılavuz hesabın erişimini; sentetik test gerçek EVREN'i; yerel credential gözlemi uzak auth/izni kanıtlamaz. `supported` yalnız capability'nin iddia ettiği düzeyde yeterli kanıtla üretilebilir. Çelişkili güncel kanıtlar görünür gerekçeyle `unknown` olur; son yazan kazanır politikası uygulanmaz. 401/403 tek başına global `unsupported` veya kesin `requires_access` değildir.

Uygulama tipli bir producer portunu çağırır; üretici seçimi composition katmanındadır. Public CLI/Python yüzeyi producer, kanıt JSON'u, `supported`, yetki listesi veya doğrulanmışlık bayrağı kabul ederek kayıt yetkilendirmez. Python nesnesinin tipli olması provenance kanıtı değildir. Aynı process/UID içindeki keyfî Python koduna karşı sandbox veya imza güvencesi iddia edilmez.

P01-3 ürün üreticisi yalnız mevcut yerel politika ve `not_verified` sonuçlarını verir. Uzak discovery/araç adaptörü yokken `unknown`/mevcut uyumsuzluk sonucu korunur. Pozitif hesap ve yürütme senaryoları yalnız test fixture producer'larında doğrulanır; ürün görev listesine test backend'i eklenmez. Gerçek hesap üreticileri P02/P03, HTTP taşıması P01-5 kapsamındadır.

### Tazelik ve saat

Yeni zamanlar kanonik UTC, altı basamak mikrosaniye ve `Z` ile yazılır. Taze koşulu `checked_at <= now < expires_at` olur; tam expiry anı stale'dir. Policy üst sınırları `supported`/`unsupported` için 300, `requires_access` için 60, `unknown` için 30 saniyedir. Producer daha kısa süre seçebilir; uzatamaz. Birleşik kayıtta en erken expiry kullanılır. Bunlar hizmet garantisi değil, ilk Yörünge politikasıdır.

Enjekte edilen saat UTC kayıt ile süreç içi monotonic deadline/yaş denetimini ayırır. Açık stateful cache/plan kullanımında kısa transaction, epoch'a bağlı kalıcı UTC high-watermark'ı ileri taşır. Clock metadata ayrıca pozitif signed-64 `clock_generation` ve `anomaly_active` taşır. `now` önceki watermark'tan geriye ilk düştüğünde aynı transaction generation'ı bir artırır ve anomaly işaretini kalıcılaştırır. Aynı geri-saat olayı sürdükçe generation yeniden artırılmaz; saat watermark'a yetişince anomaly kapanır. Taşma kontrollü hata olur, sayaç sarmaz veya otomatik reset olmaz.

Cache, plan ve onay etkinliği **güncel clock generation** ile de eşleşmelidir. Anomali öncesi kayıtlar saat yetiştikten veya süreç yeniden açıldıktan sonra canlanmaz. Yeni refresh de anomaly sürerken kritik geçerlilik vermez. İleri sıçrayıp süresi bitmiş kayıtların saat geri dönünce canlanması aynı kapıyla engellenir. Gelecekteki veya bozuk producer zamanı kabul edilmez. Clock generation'ın ilerletilmesi, kullanım senaryosunun sonraki hata/ret nedeniyle rollback ettiği bir transaction içinde kaybolamaz; ret öncesi ayrı kısa kalıcı saat denetimi tamamlanır. Son cache/plan/onay commit'i bu neslin değişmediğini tekrar doğrular.

Güvenilir dış saat yokken gözlenmeyen saat geri dönüşünü veya DB+K+clock metadata'sının birlikte eskiye alınmasını tam saptama iddiası yoktur. Persist edilmiş monotonic sayaç restart otoritesi olarak kullanılmaz. Cache tazeliği **yan etki yetkisi değildir**: kritik execution/approval geçerliliği [ADR-0014](0014-execution-plan-validity-and-approval.md) uyarınca güncel trusted producer doğrulaması ister.

Normal stateful sorgu miss/stale/clock-anomaly durumunu açık gösterir; eski `supported` yalnız tarihsel kayıt olarak sunulur, etkin karar `unknown` olur. `--refresh` hatası eski başarıyı güncellemez veya geçerli kılmaz; kontrollü hata ve güvenli önceki kayıt korunur. `--cached` discovery yapmaz. Hiçbir yol sınırsız/otomatik refresh döngüsü açmaz.

### Transaction ve saklama

Cache yazımı/etkin okuması son kısa transaction'da store/epoch/clock generation ve kullanılan bütün credential ID/revision bağlarını tekrar denetler. Arada gözlem değişmişse `state_changed` olur; eski snapshot tekrar observe edilmez, env ikinci kez okunmaz ve otomatik retry yoktur. Ağ/hash işlemi SQL write transaction'ı dışında kalır. Açık cache kullanımının toplam bütçesi 5 saniye, lock/busy beklemesi en çok 1 saniyedir; disk I/O için katı duvar saati garantisi iddia edilmez.

Bir kanonik cache kaydı en çok 32 KiB, en çok sekiz kanıt ve 128 izin/kaynak öğesi taşır. Etkin credential binding/nesil başına 128, store genelinde 1.024 kayıt sınırı vardır; credential'sız local kayıtlar epoch'a bağlı tek kota grubudur. Upsert transaction'ı önce eski epoch/nesil kayıtlarını, sonra expiry ve en eski doğrulama zamanı/anahtar sırasıyla kota fazlasını temizler. Eski nesil kayıtları aktif cache'te birikmez. Bu yalnız türetilmiş cache'e uygulanır; identity geçmişi, plan, onay, operation veya backup silinmez. Sınır mantıksal payload/satır sınırıdır; SQLite dosyasını küçültmek için otomatik VACUUM yapılmaz.

Gerçek tüketiciyle yeni immutable SQL migration eklenir; eski migration/checksum değiştirilmez. Şema sürümüne duyarlı full validation, backup ve sıcak tek-kayıt doğrulaması yeni payload/değişmezleri kapsar. Reset/restore yeni epoch kurunca cache etkinliğini yitirir. Restore/recover genişlemesinin sınırı ADR-0014'tedir.

### Public yüzey ve uyumluluk

Mevcut `capabilities` varsayılanı ve `api.inspect_capabilities` offline/stateless kalır. Açık `capabilities --cached|--refresh [--state-dir PATH]` yeni cache sorgusunu seçer; seçenekler birbirini dışlar. Python karşılığı ayrı `api.query_capabilities(..., refresh=False, state_dir=None)` kullanım senaryosudur. Açık yol private state/clock metadata yazabilir, uzak görevde yalnız seçili hizmet env'sini bir kez gözleyebilir; uzak discovery bu sürümde yoktur. `--refresh` ağ bağlantısı varmış gibi anlatılmaz.

JSON sonucu cache hit/miss, freshness, etkin karar ve varsa tarihsel kaydı ayırır. Sorgunun `unknown` dönmesi başarılı sorgu olabilir; malformed istek/state/binding çatışması kontrollü hatadır. Yeni public alanların ayrıntısı onay sonrası capability/CLI referansında tek yerde sabitlenir; eski offline JSON'a bu alanlar eklenmez.

## Değerlendirilen alternatifler

- **v1'i yerinde genişletmek:** Eski offline dosyanın anlamını ve yeniden hesaplama kuralını bulanıklaştırır; ayrı v2 seçildi.
- **Caller JSON'u veya doğrudan cache import:** Kanıt ile iddiayı karıştırır; production admission yolu değildir.
- **TTL'siz/sınırsız cache veya revision'sız anahtar:** Eski yetki ve sınırsız büyüme riski; reddedildi.
- **Her komutta bütün endpointleri taramak:** P01 kapsamını ve kaynak bütçesini aşar. Açık, görev kapsamlı producer çağrısı seçildi.
- **Sadece UTC veya sadece monotonic:** İlki gözlenen saat geri dönüşünde kayıt canlandırabilir; ikincisi restart için güvenilir kalıcı zaman değildir. Sınırlı birleşik yaklaşım ve kritik yeniden doğrulama seçildi.

## Sonuçlar

Onay; ayrı v2 kayıt, kaynak güven sınırı, sayısal cache/TTL politikası ve açık stateful sorguyu kapsar. Canlı hesap desteği, yeni bağımlılık veya yan etki yetkisi vermez. Ürün kabulü [P01-3a kartında](../roadmap/tasks/p01-3a-scoped-capability-cache.md); bu öneri kabul/test kanıtı değildir.
