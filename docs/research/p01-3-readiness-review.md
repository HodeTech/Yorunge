# P01-3 belge, sözleşme ve uygulama hazırlığı incelemesi

**Tarih:** 2026-10-27. **Durum:** Hazırlık/karar önerisi; ürün kodu ve P01-3 kabulü değildir. **Taban:** development@78d5d77; **dal:** feat/p01-3-capability-planning.

## Sonuç ve onay kapsamı

P01-2b/P01-4a önkoşulları development'ta doğrulanmış durumda; mevcut SQLite, HMAC/epoch/nesil ve hedef normalleştirme kararlarını yeniden açmak gerekmiyor. P01-3 satırı tek başına uygulamaya hazır değil: kanıt otoritesi, cache politikası, ayrı execution biçimi/onayı ve yeni state tüketicilerinin bakım davranışı ayrıntısızdı. Bunlar rutin kodlama tercihi değil, public sözleşme/güven sınırıdır.

Önerilen iki karar [ADR-0013](../decisions/0013-scoped-capability-cache.md) ve [ADR-0014](../decisions/0014-execution-plan-validity-and-approval.md) içinde somutlaştırıldı. İkisi de **Proposed**; kullanıcı onayından önce runtime, test davranışı veya Accepted sözleşme değiştirilmez. Uygulama sırası [paket planında](../roadmap/p01-3-delivery-plan.md), ayrıntılı kabul iki iş kartındadır.

## İnceleme kapsamı

Root incelemesine ek üç bağımsız salt okuma ajanı kullanıldı: `p013_preflight_contracts` (GPT-6.1 Sol/high), `p013_preflight_state` (GPT-6 Astra/high), `p013_preflight_surfaces` (GPT-6.1 Sol/high). Alanlar sırasıyla karar/belge tutarlılığı, state/güvenlik/yarışlar ve CLI/Python/eski dosya uyumluluğudur. Ajan iddiaları mevcut kod ve belgelerle tekrar karşılaştırıldı; olası yeni tüketici riskleri mevcut P01-2 kusuru gibi sunulmadı.

| Belge/kod kümesi | İncelenen sınır |
|---|---|
| AGENTS, ajan rehberi ve implement/plan/contract/review/verify/PR skill'leri | Yetki, tek epik PR, hazır kart, doğrulama ve iki review turu |
| current, ürün kapsamı, matris, P01, roadmap/task şablonu/indeksi | Gerçek teslim, alt işler, önkoşul ve P01-4/5/P02/P03 ayrımı |
| İlkeler, architecture/Python/UX/performance/testing/security/error/documentation/Git standartları, CONTRIBUTING | Bağımlılık yönü, lazy import, hata/JSON, kaynak ve teslim kapıları |
| Architecture overview/execution/data-and-state/integration-boundaries; capability/workflows/identity modülleri | Plan/yetki/secret snapshot, kalıcılık ve alan sahipliği |
| ADR-0004/0005/0008/0011/0012; capability/credential-binding/configuration/local-state/CLI/tool-provider referansları | Kesinleşmiş kararlar ve henüz somutlaşmamış sözleşmeler |
| P01-2b/P01-4a kartları ve P01-2 kabul kaydı, readiness review, README/CHANGELOG/proje yapısı | Önkoşul kanıtı, tarihsel kayıt ve destek iddiası |
| Domain models/credentials/state/maintenance; application planning/credentials; API/CLI/files/state/schema/identity/maintenance ve ilgili testler | Gerçek v1 davranışı, migration, restore intent ve entegrasyon noktaları |

Bu hazırlıkta ürün test takımı, yeni build, benchmark veya canlı EVREN deneyi yapılmadı. Önceki 837 test sonucu P01-2'nin tarihsel kanıtıdır; P01-3 başarısı değildir. Yeni belgelerin yapısal kontrolleri ve review sonucu teslim planının hazırlık kaydına yazılır.

## Doğrulanmış boşluklar ve aksiyonlar

| Gözlem | Mevcut kaynak | Aksiyon |
|---|---|---|
| Cache yenileme/eski kanıt davranışı açık bırakılmış | [ADR-0005](../decisions/0005-capabilities-and-contracts.md), [capability](../reference/capability-record.md) | ADR-0013: producer yetkisi, tam scope, TTL/saat, çatışma ve saklama sınırı |
| Offline model credential/zaman/tool sürümünü null, Plan durumunu draft/false ile kısıtlıyor | [models](../../src/yorunge/domain/models.py), [offline builder](../../src/yorunge/application/planning.py), [load_plan](../../src/yorunge/api.py) | V1'i koruyan ayrı v2 capability/execution modelleri; dosya yüklemeyi execution onayına dönüştürmeme |
| Model kimliği/sürümü genel referansta var, mevcut dar Scope'ta yok; authorization kapsamının biçimi tanımsız | [capability sözleşmesi](../reference/capability-record.md) | Yeni scope'ta model, environment ve tipli kaynak/izin bağlarını açık tutma; null wildcard değil |
| Gözlem kendi transaction'ında commit oluyor; sonraki tüketicide arada revision değişebilir | [identity](../../src/yorunge/adapters/identity.py), [credential portu](../../src/yorunge/application/credentials.py) | Son cache/plan/approval transaction'ında etkin epoch ve credential ID/revision tekrar kontrolü; otomatik retry yok |
| Reset eski binding satırlarını koruyor | [maintenance](../../src/yorunge/adapters/maintenance.py) | Bütün yeni tüketicilerde etkin store/epoch kapısı; local-only plan/onay da bağlı |
| Restore/recover runtime kapısı yalnız üç identity tablosuna izin veriyor | [maintenance](../../src/yorunge/adapters/maintenance.py), [local-state](../reference/local-state.md) | ADR-0014: açık cache/plan/onay allowlist'i; operation runtime yasağı korunur; preview kayıp kapsamı ve eski intent recovery tamamlanır |
| Eski geçerli stage/live shortcut'ı yeni runtime şemasına migration'ı varsaymamalı | [maintenance](../../src/yorunge/adapters/maintenance.py) | Stage yok/eski stage/eski live ve kaynak backup kayıpken tamamlanmış çift kabulü yeni tüketiciyle test edilir |
| Hazır P01-3 kartı ve epik planı yok | [faz](../roadmap/phase-01-core.md), [kart indeksi](../roadmap/tasks/README.md) | İki draft kart ve dört uygulama adımı; karar onayıyla ready kapısı değerlendirilecek |
| Proje yapısı hâlâ SQLite adaptörünü uygulanmamış sayıyor | [proje yapısı](../project-structure.md) | Mevcut P01-2 kaynak yerleşimiyle düzeltildi; yeni P01-3 implementasyonu varmış gibi yazılmadı |
| Yolculuk girişindeki bugünkü alt küme P01-2'den geride; state mimarisi Accepted restore kapısına hâlâ öneri diyor | [yolculuklar](../user-journeys.md), [state mimarisi](../architecture/data-and-state.md) | Yerel P01-2 teslimi ve mevcut kararın durumu düzeltildi; uzak akışlar ve yeni P01-3 önerisi planlandı kalır |

Mevcut v1 `load_plan`, saklanan context/selection/recipe ile offline politikayı yeniden kurup eşitlik denetler; sadece yeniden hesaplanmış digest'e güvenmez. Bu koruma kaldırılmaz. Yeni JSON şemasının strict olması veya nesnenin Python tipi, bağımsız provenance/onay kanıtı değildir.

## Araştırma dayanağı ve çıkarımlar

Aşağıdaki resmî kaynaklar 2026-10-27 tarihinde incelendi; bir hizmetin canlı davranışını veya seçilen sayısal ürün politikasını kanıtlamaz:

| Kaynak | Kanıt ve tasarım çıkarımı |
|---|---|
| [Python 3.11 time](https://docs.python.org/3.11/library/time.html) | Monotonic saat sistem saatinden etkilenmez; yalnız fark anlamlıdır. Çıkarım: UTC kayıt ve kullanım süresi ayrılmalı, monotonic değeri reboot sonrası kalıcı otorite sayılmamalı |
| [Python 3.11 json](https://docs.python.org/3.11/library/json.html) | JSON boyut sınırı, sıralı/kompakt encoding ve NaN/duplicate davranışı açıkça kontrol edilmelidir. Çıkarım: bounded strict payload ve sabit canonical encoding |
| [Python 3.11 hashlib](https://docs.python.org/3.11/library/hashlib.html) | İçerik digest'i güncel okunan baytlardan hesaplanabilir. Çıkarım: digest alanını görmek dosya içeriği veya kaynağın yetkisini doğrulamaz; dosya yaşam döngüsü ayrıca korunur |
| [SQLite transactions](https://www.sqlite.org/lang_transaction.html) | Read transaction eski snapshot'ı görebilir; eşzamanlı tek writer vardır, BEGIN IMMEDIATE busy olabilir. Çıkarım: gözlemden sonra commit öncesi aynı kısa transaction içinde kritik bağ kontrolü gerekir |
| [SQLite STRICT](https://www.sqlite.org/stricttables.html) | STRICT tablo kayıpsız tür dönüşümünü hâlâ yapabilir. Çıkarım: SQL sınırları tipli payload/UUID/zaman/ilişki doğrulamasının yerine geçmez |

TTL 300/60/30 saniye, cache kotası, plan kotası ve ayrı public komutlar dış standarttan çıkmaz; önerilen Yörünge seçimleridir ve ADR onay kapsamındadır. Başka sağlayıcının doğrulanmamış auth/capability endpoint'i veya izin adı uydurulmadı. Mevcut EVREN araştırması bu pakette canlı keşif adaptörü kurmak için yeterli sayılmadı; P02 kapısı korunur.

## Kullanıcıya sunulan kararlar

1. **ADR-0013 önerisi:** Offline v1 korunurken ayrı v2, trusted producer sınırı, sınırlı TTL/cache ve açık stateful sorgu. Kullanıcıya kanıt JSON'u yükletip uzak supported iddiası kabul edilmez.
2. **ADR-0014 önerisi:** Ayrı kalıcı execution hazırlığı/validity/onay, açık revoke/forget, yeni epoch'la bütün bağların geçersizliği ve operation öncesi dar restore/recover devamlılığı. Bakım önizlemesinin v2 çıktı farkı açıkça belgelenir.

İki öneriyi birlikte uygulamak için yeni uzak hesap erişimi, ücretli işlem, araç kurulumu, repo izin değişikliği veya dependency seçimi gerekmiyor. Bu aşamada başka kullanıcı tercihi saptanmadı. Onay sonrası yeni güven sınırı/ADR ihtiyacı doğarsa o karar önce somutlaştırılır; rutin uygulama ayrıntısı tekrar onaya taşınmaz.
