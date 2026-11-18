# P02-4 — Katalog, sabit referans ve seçilmiş ağırlık teslim planı

**Tarih:** 2026-11-19. **Durum:** Uygulama başladı. İki fresh review turu ve belge incelemesinin bulguları işlendi; [ADR-0035](../decisions/0035-catalog-reads-fixed-references-and-selection.md) Accepted (2026-11-19). ADR dışındaki kararlar aşağıdaki tabloda önerilerle uygulanır (kullanıcı talimatı). **Dal:** `feat/p02-4-catalog-and-selection`, `origin/development` `1a36c8d` tabanı. Tek development PR; Master ve release kullanıcıdadır.

## Kullanıcı sonucu

Model veya veri sorumlusu, anahtarının eriştiği Platform modellerini tek sayfa olarak listeler, `owner/slug` ile bir modeli açar, sürümlerin etiketlerini ve biçimlerini görür (**P02-4a**). Bulduğu sürümü kimlik kopyalamadan `--model OWNER/SLUG --version-tag TAG` ile seçip ağırlığını doğrulama seviyesiyle indirir; belirsiz veya bulunamayan seçimde ağırlık isteği yapılmaz (**P02-4b**). LLM geçidinin bu anahtara görünen modelleri, görevleri ve kullanım bilgisi görünür; P02-5 model/görev eşleşmesini buradan doğrular.

## Mevcut eksik

- `models download` yalnız `--version-id` kabul eder; kimliği Platform arayüzünden kopyalamak zorundadır ([P02-3n](tasks/p02-3n-model-weights-consumer.md)).
- Platform modellerini ve veri setlerini listeleyen, `owner/slug` çözen veya sürüm etiketini bulan komut yoktur.
- LLM `ModelInfo` hiçbir yerde okunmaz; P02-5 için model/görev doğrulaması kaynağı yoktur.
- [Katalog modülü](../modules/catalog-models.md) ve C05 satırı “planlandı”dır.

## Giren ve girmeyen kapsam

**Girer:**

- Platform modelleri: tek sayfa liste (`page`, `page_size`), `owner/slug` detayı, `model_id` ile sürüm listesi.
- Platform veri setleri: tek sayfa liste (`GET /datasets`; tamlık başlıklarla); kapsam K2’ye bağlı.
- LLM modelleri: liste, `model_id` detayı, istemci tarafı `task` filtresi ve görev doğrulaması.
- Çözüm: `owner/slug` + `version_tag` (Platform); `model_id` + beklenen `task` (LLM).
- `models list`, `models show`, `datasets list`; ortak Python API; metin/JSON/NDJSON çıktıları; dört yeni kararlı hata kodu (K11).
- `models download --model OWNER/SLUG --version-tag TAG` seçim yolu ([ADR-0035](../decisions/0035-catalog-reads-fixed-references-and-selection.md) §6).
- [P02-R10](tasks/p02-r10-llm-terms-guidance.md) (K7), ayrı kart ve ayrı commit.
- Canlı salt okuma kabulü (K4) ve canlı indirme kabulü (K5, ayrı onay).

**Girmez:** kalıcı önbellek; “en iyi/önerilen model” sıralaması; statik kaldırılma tablosu; Platform `selectable-models` ve llm-portal görünümleri; lisans veya şart kabulü; dataset baytı indirme ([P02-R5](tasks/p02-r5-dataset-item-byte-access.md)); sürüm oluşturma/freeze ([P02-R4](tasks/p02-r4-dataset-version-creation.md)); warmup, benchmark, rezervasyon veya ücretli çıkarım; GPU/kota ([P02-6](phase-02-data-and-inference.md)); LLM çıkarım çağrıları ([P02-5](phase-02-data-and-inference.md)); profilde kalıcı “aktif model”; otomatik sayfa döngüsü; profil/proje seçenekleri (`--profile`, `--config`, `--project`; hesap aktif profilden gelir, `models download` ile aynı kural); dosyaya yazma seçeneği (liste tek sayfa ve en çok 100 kayıttır; uzun çıktı için JSON/NDJSON stdout yönlendirmesi vardır, [UX standardının](../standards/ux.md) dosya seçeneği bu kapsamda gereksizdir).

## Bağımlılıklar

| Bağ | Durum | Kanıt |
|---|---|---|
| P02-0a sözleşme/SDK | verified | [kart](tasks/p02-0a-contract-sdk-pilot.md), PR #12 |
| P02-0c LLM context/terms (Bearer yolu) | verified | [kart](tasks/p02-0c-llm-context-discovery.md), PR #12 |
| P02-0d Platform context (X-API-Key yolu) | verified | [kart](tasks/p02-0d-platform-context-discovery.md), PR #12 |
| P01-3a cache kuralları, P01-5a ortak HTTP taşıması | verified | PR #8, #11 |
| P02-3b ortak indirme, P02-3n `models download` | verified (canlı kabul yok) | [P02-3b](tasks/p02-3b-download-acceptance.md), [P02-3n](tasks/p02-3n-model-weights-consumer.md), PR #15 |

Bağımlılıkların tamamı development’ta verified/teslimdir. P02-4c, ADR-0035 Accepted olduktan sonra `ready` olur. Diğer adım kartları kendi `depends_on` zincirini bekler; hiçbiri ADR onayından önce `ready` yapılmaz. Canlı erişim için mevcut yerel pilot anahtarları kullanılır; anahtar değerleri bu belgeye veya kanıta yazılmaz.

## Kullanıcı kararları (P02-4 K1–K11)

ADR’de yer alan kararlar (K1, K6, K9, K11) [ADR-0035](../decisions/0035-catalog-reads-fixed-references-and-selection.md) Accepted ile onaylanmıştır. Diğerleri kullanıcı talimatıyla **önerileriyle** uygulanır; her biri aşağıda işaretlidir.

| # | Karar | Durum |
|---|---|---|
| K1 | ADR-0035: yalnız GET; LLM kimliği gateway’den; tek sayfa semantiği ve tamlık durumları; kalıcı önbellek yok; “sabit” = gözlemlenen kimlik; seçim bağı; dar tüketici codec | **Accepted (2026-11-19)** |
| K2 | Veri seti listesi: `GET /datasets` (sayfa `page`/`page_size`; tamlık `X-Has-Next`); `scope=owned` isteği gönderilir, ama çıktıdaki kapsam etiketi K4 teyidine kadar `unknown` kalır | Öneri uygulanır |
| K3 | LLM model kaynağı: gateway `GET /v1/models`; Platform `selectable-models` P02-4’te yok | Öneri uygulanır |
| K4 | Canlı salt okuma: yerel pilot anahtarlarıyla yalnız GET, ≤20 mantıksal istek; yazma, ücretli çağrı, indirme yok. Teyit: sayfa üst sınırı, sunucunun sayfa boyutunu düşürme davranışı, `X-Has-Next`/`X-Total-Count` biçimi, `scope` etkisi, LLM kimlik alfabesi, en büyük gerçek sayfa boyutu | Öneri uygulanır |
| K5 | Canlı indirme: erişilebilir bir sürüm kimliği kullanıcı tarafından verilmediği sürece yapılmaz; kabul “yapılmadı” olarak kaydedilir | Öneri uygulanır (sürüm kimliği bekleniyor) |
| K6 | Seçim sözdizimi `--model OWNER/SLUG --version-tag TAG`; `--version-id` korunur; “en son” yok; motor sırası ve kilit kapsamı ADR-0035 §6 | **Accepted (2026-11-19)** |
| K7 | P02-R10 ayrı kart ve ayrı commit (adım 5); katalog hata yoluna genişletilmez | Öneri uygulanır |
| K8 | UX: bulma yolu `models list` → `models show --versions` → `models download --model --version-tag`; owner’sız model için `show --model-id --versions` ve `download --version-id`; hesap `--config`/`--profile` ile veya aktif profilden; belirsizlikte 0 ağırlık isteği; süre/yardım/yanlış hedef ölçümü P02-7’de | Öneri uygulanır |
| K9 | Codec: dar tüketici (ADR-0022 deseni; okunmayan alan çıktıya girmez; ham ağaçta gizli tarama; DTO’lar kapalı). K9-B kapalı tam şekil reddedildi | **Accepted (2026-11-19)** |
| K10 | Dal `feat/p02-4-catalog-and-selection`, tek development PR, adım başına commit ve iki fresh review turu; PR en sonda, merge kullanıcıda | Öneri uygulanır |
| K11 | Hata çıkışları: `model_not_visible` çıkış 1; `model_ambiguous`, `model_task_mismatch`, `model_not_addressable` çıkış 2 | **Accepted (2026-11-19)** |

## Adımlar ve review döngüsü

Her kod adımı: **geliştir → ilgili gerçek kontroller → commit → fresh review R1 → doğrulanmış bulgu/fix/commit → farklı fresh reviewer R2 → doğrulanmış bulgu/fix/commit**. Reviewer bulguları ve kod untrusted veri sayılır; güncel kodla doğrulanır; sonuçsuz tercih yeni bug diye sunulmaz. Reviewer modeli ve effort’u riske göre seçilir: varsayılan `sonnet` (yüksek effort); ağ/sır/state gibi güvenlik-kritik adımlarda `opus` (yüksek effort); `fable` yalnız kullanıcı istediğinde.

| Adım | Kart | Review eksenleri | Tek sonuç / kapı |
|---|---|---|---|
| 0 | Hazırlık: bu belge, ADR-0035, kartlar, indeksler | belge tutarlılığı · sözleşme/güvenlik · UX | R1, R2 ve belge incelemesi tamam; ADR-0035 Accepted; hazırlık commit’i `7247867` ve düzeltme commit’i |
| 1 | [P02-4c](tasks/p02-4c-catalog-contract.md) | sözleşme/oracle · güven sınırı | Dar tüketici tipleri (K9), tamlık ve çözüm kuralları, sınırlar, sanitizasyon, `docs/reference/catalog.md` |
| 2 | [P02-4d](tasks/p02-4d-catalog-transport-api.md) | ağ güvenliği · sır sızıntısı · test | GET adaptörleri, tek sayfa, yanıt/süre sınırları, retry, `api.py` fonksiyonları, loopback TLS entegrasyonu |
| 3 | [P02-4e](tasks/p02-4e-catalog-cli-acceptance.md) (CLI) | UX/CLI sözleşmesi · belge | `models list/show`, `datasets list`, metin/JSON/NDJSON, dört yeni hata kodu, [cli-contract](../reference/cli-contract.md) güncellemesi (taslak `llm models` örneği dahil), süreç testleri, kurulu CLI smoke |
| 4 | [P02-4e](tasks/p02-4e-catalog-cli-acceptance.md) (canlı) | kanıt/gizlilik · canlı sınır | K4 kapsamında canlı salt okuma; teyit maddeleri; P02-4a üst kabulünün canlı bölümü |
| 5 | [P02-R10](tasks/p02-r10-llm-terms-guidance.md) | UX metni · güvenlik sınırı | Tek satır yönlendirme ve testler (K7) |
| 6 | [P02-4f](tasks/p02-4f-selected-download-binding.md) | state/güvenlik · sözleşme | `--model/--version-tag` çözümü; motor sıra ayrıştırması ve regresyonu; hata eşlemesi; download-engine referansı |
| 7 | [P02-4f](tasks/p02-4f-selected-download-binding.md) (canlı) | kanıt · canlı sınır | K5 varsa tek canlı indirme kabulü; yoksa “yapılmadı” |
| 8 | [P02-4a](tasks/p02-4a-catalog-acceptance.md), [P02-4b](tasks/p02-4b-selected-download-acceptance.md), belgeler | belge tutarlılığı · uçtan uca kabul | Üç komutlu bulma yolunun uçtan uca kabulü (K8b); üst kartlar, [C05](../capability-matrix.md), [modül](../modules/catalog-models.md), [current](current.md), [faz](phase-02-data-and-inference.md) ve PR |

**Büyüme kuralı.** Bir adım ölçülen kapsamıyla S/M sınırını aşarsa iş küçültülmez; yeni kart harfi ve bu tabloda kayıt ile bölünür.

**Otomatik ilerleme ve durma.** Bir adım R2 sonrası temiz kapanınca kullanıcıya dönmeden sonraki adıma geçilir. Yalnız şu durumlarda durulur: (a) yeni veya değişen ADR, DDL/migration ya da kapsam küçültme gerekirse; (b) K4/K5/K9’da onaylanmamış canlı veya codec yetkisi gerekirse; (c) çözülemeyen engelleyici hata olursa.

## UX, performans ve güvenlik teyidi

**Kullanım kolaylığı.**

- Komut adları mevcut `models download` ile tutarlıdır: `models list --service evren-platform|evren-llm`, `models show`, `datasets list`, `models download --model --version-tag`.
- `--service` zorunludur; komut hangi hizmeti okuduğunu her zaman söyler.
- Çıktı tek sayfa, gözlem zamanı, tamlık durumu ve sonraki komut ipucunu verir. Otomatik sayfa yoktur; çıktı sessizce uzamaz.
- Boş sonuç “bu anahtara görünen model yok” der; “yok” veya “kaldırıldı” demez.
- Belirsiz `version_tag` çözümünde en çok beş aday (kimlik, etiket, tarih) gösterilir; Yörünge aday seçmez.
- `owner` olmayan model listede model kimliğiyle görünür ve çıkış yolu (`--model-id --versions`) ipucunda yazılır.
- Hata metni bir sonraki eylemi söyler: hesap/profil kontrolü, sayfa değişikliği, etiket bulma.
- JSON/NDJSON çıktıları saf kalır; non-TTY ortamda prompt yoktur; metin çıktısı renksiz okunur.

**Performans.**

- Her komutun ağ çağrısı sayısı sabittir: liste 1, detay 1, `model_id` ile sürüm listesi 1, `--versions` ile detay 2, veri seti listesi 1; çözüm en çok 2 GET’tir. Liste satırları için model başına detay çağrısı yapılmaz (N+1 yok).
- Bellek ve yanıt sınırları: tek yanıt en çok 1 MiB; Platform sayfası en çok 100 kayıt (üst sınır K4 ile teyit); LLM listesi en çok 500 kayıt; komut toplamı en çok 30 s; her okuma en çok iki deneme (ADR-0017, yalnız salt okuma GET).
- Platform sayfa boyutu istemci varsayılanı 20; sunucu davranışı K4 ile teyit edilir.
- Startup ve import: katalog kodu tembel yüklenir; yardım ve yerel komutlar ağ veya katalog modülü yüklemez. Import grafiği değişirse [startup kapısı](../standards/performance.md) yeniden ölçülür.

**Güvenlik.**

- Platform anahtarı yalnız `X-API-Key` olarak, LLM anahtarı yalnız `Authorization` olarak kayıtlı origin’e gider; yönlendirme izlenmez; hata metninde ve çıktıda sır yoktur.
- Adres segmentleri (`owner`, `slug`, `model_id`, `version_id`) `[A-Za-z0-9._-]{1,128}` ile sınırlıdır; `.` ve `..` yasaktır; `%`, `/` fazlası, `?`, `#`, boşluk ve kontrol karakteri I/O öncesi reddedilir. Böylece çift kodlama ve yol enjeksiyonu yüzeyi kapanır.
- Katalog metinleri terminal kontrol ve çift yönlü karakterlerden arındırılır, uzunluğu sınırlanır, yol/URL/komut olarak kullanılmaz.
- Depolama adresleri çıktıya girmez ve takip edilmez; ağırlık adresi yalnız P02-3n akışından gelir.
- Yanıt codec’i K9 kararına göre dar tüketicidir; ham ağacın tamamında seçili anahtar için literal-secret taraması yapılır.
- Şart, lisans veya erişim kabulü otomatik yapılmaz; `pricing`/`free_until` maliyet kapısı değildir.
- Tamlık ve görünürlük iddiası kanıtsız yapılmaz; kapsam kanıtlanmadıkça `unknown` yazılır.

**Kaynak bütçesi.** Katalog komutu: ≤2 GET (seçim yolunda çözüm ≤2 GET, sonra +1 JSON ve motor), yanıt ≤1 MiB, katalog süresi ≤30 s (indirme deadline’ından ayrı), bellekte en çok bir sayfa. İndirme süresi `--timeout` ile ayrıca sınırlıdır. Bu sayılar ölçülmeden kabul edilmez; kartlar bunu kabul maddesi yapar.

**Doğrulanamayan konular (K4 ile teyit).** Platform sayfa üst sınırı (100), `X-Has-Next` ve `X-Total-Count` değer biçimi, `scope` davranışı, `model_card` gibi büyük alanların 1 MiB sınırına etkisi, LLM kimlik alfabesi, `GET /models/{model_id}/versions` yanıtının sayfalama davranışı.

## Kabul ve kanıt planı

- **P02-4c (sözleşme):** Her tüketilen alan için olumlu ve negatif oracle; zorunlu alan eksikliği, tip yanlışlığı, duplicate key, NaN, sınır aşımı; tamlık formülü (`(p-1)*s + n >= t`) ve başlık durumları; belirsiz ve sıfır sonuçlu çözüm; `owner_username` null; `.`/`..` ve alfabe dışı segment; görev uyuşmazlığı; sanitizasyon; depolama adresi görünmezliği. Fixture’lar resmî şema özetinden türetilir; kişisel veri ve gerçek kimlik içermez.
- **P02-4d (taşıma):** Loopback TLS sahte Platform ve LLM; yanlış origin, yönlendirme reddi, 401/403/404/408/429/5xx eşlemesi; iki denemenin sınırı; anahtar sızıntı sentinel’i; istek sayımı ve bayt/süre sınırı kanıtı; yanlış hedefe 0 istek.
- **P02-4e (CLI ve canlı):** Gerçek süreç testleri (yardım, çıktı kipleri, exit kodları, SIGINT, kapalı stdout, eksik `--service`, LLM’de sayfa bayrağı); kurulu wheel smoke’u; K4 kapsamında canlı GET kaydı (sayılar, görev dağılımı, alan kümesi, başlık biçimleri, üst sınır; kimlik ve ad maskeli; [kanıt standardı](../standards/research-evidence.md)).
- **P02-4f (seçim bağı):** Çözüm başarısızsa ağırlık isteği yok; ağsız yerel ön kontrol hatalarında hiç GET yok; belirsizlikte ağırlık isteği yok; çözülen `version_id` ile tek JSON çağrısı; `--version-id` yolu ve motor davranışı regresyonsuz; farklı çözülen sürümde önceki kısmi içeriğin atıldığı kanıtı; K5 varsa canlı indirme kabulü, yoksa “yapılmadı”.
- **Kapılar:** Ruff format/lint, strict mypy, hedefli ve tam test paketi, `check-docs.py`, `check-agent-guides.py`, `git diff --check`, build ve temiz kurulum; import/startup değişirse ilgili M5 kapısı. Çalıştırılmayan kontroller açıkça yazılır.

## Teslim kaydı

Hazırlık aşamasında boş. Adım sonuçları ve PR bilgisi gerçekleştikçe bu belgeye ve kartlara eklenir.
