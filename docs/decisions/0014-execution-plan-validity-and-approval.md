# ADR-0014: Execution planı, geçerlilik ve digest bağlı onay

**Durum:** Proposed — kullanıcı onayı bekliyor; ürün uygulaması başlamadı. **Tarih:** 2026-10-27. **İş:** P01-3b; P01-3a bakım entegrasyonu. [Ön inceleme](../research/p01-3-readiness-review.md), [teslim planı](../roadmap/p01-3-delivery-plan.md).

## Bağlam

Mevcut Plan v1 yalnız offline draft'tır. SHA-256 digest bütünlük denetimidir; auth, içerik doğrulaması veya insan onayı değildir. [Execution tasarımı](../architecture/execution-model.md) kritik bağları ve yan etki öncesi sırayı kabul eder, fakat somut execution şeması, geçerlilik/onay ömrü ve P01-3 restore davranışı henüz yoktur.

Bu öneri mevcut offline davranışı, [ADR-0011](0011-state-foundation-and-migrations.md) dayanıklılığını ve [ADR-0012](0012-credential-identity-and-change-detection.md) credential bağlarını koruyarak eksik sınırı tanımlar. Operation/attempt/lease ve taşıma bu pakete taşınmaz.

## Önerilen karar

### Ayrı, değişmez execution hazırlığı

`ExecutionPlan` ayrı `schema_version=2`, `mode=execution` biçimidir. Eski Plan v1 üretimi, `plan show`/`api.load_plan`, saved seçimler ve digest baytları aynen kalır; v1 dosyası execution planına otomatik yükseltilmez. Yeni plan store'a UUIDv4 ile kaydedilen değişmez bir snapshot'tır; güncel profilden yeniden seçim yapılarak içeriği değiştirilmez.

Digest'e giren alan grupları:

| Alan grubu | Bağlanan bilgi |
|---|---|
| Kimlik/sürüm | Plan ID, schema/policy sürümü, store ID, identity epoch ve clock generation; local-only plan da bağlıdır |
| İstek/seçim | Görev, tipli parametreler, seçilen tool/execution ve seçim kaynağı |
| Girdiler | Rol, sabit kök/göreli yol, güncel içerik SHA-256/boyut; model/veri sürümü ve varsa doğrulanmış içerik bağları |
| Araç/ortam | Doğrulanmış sürüm/executable/environment/runtime kimliği; gerekli izinler ve parametre eşleme/kayıp raporu |
| Hizmet/yetki | Kullanılan her hizmetin tam hedef, hesap/proje, credential ID/revision ve doğrulanmış authorization scope'u |
| Kanıt | Gerekli capability kararları, kaynak/politika sürümü, kapsam, kontrol/expiry zamanları |
| Etki/bütçe | Tipli etkiler, açık deadline, varsa tahminin kaynağı/tarihi/süresi; bilinmeyen maliyet null olarak görünür |
| Hazırlık sınırı | Hazırlanma/son geçerlilik zamanı, doğrulama durumu ve engeller |

Kanonik JSON kodlaması ADR-0013 ile aynıdır; yalnız `digest` hariç bütün plan gövdesi hash'lenir. Secret, env referans adı, HMAC/tag veya K dahil edilmez. Plain SHA-256 imza veya provenance kanıtı diye kullanılmaz. Persist edilmiş plan okunurken şema/digest/ilişkiler denetlenir; public dosya import'u veya caller `verified/approved` iddiası kabul edilmez.

### Girdi ve güncel bağ doğrulaması

Yerel dosya bağlama açık `input_root` altında, kök dahil symlink içermeyen düzenli dosyalarla yapılır. Absolute/kök dışı/dot traversal referansı reddedilir. Hash sınırlı bloklarla, monotonic toplam bütçesi altında ve SQL write transaction'ı dışında hesaplanır; descriptor/stat değişimi denetlenir. Aynı boyut/mtime veya eski hash cache'i güncel içerik yerine geçmez. Mevcut recipe'deki `data.manifest` için yalnız dosyanın kendi içeriği bağlanır; içerikteki bütün veri dosyalarının doğrulandığı iddia edilmez. Model revision etiketi tek başına değişmez model içeriği değildir. Görev adaptörünün tam girdi kapanışı doğrulanamıyorsa plan blocked kalır.

Execution prepare/validate/approve toplam bütçesi 30 saniye, bir hash bloğu en çok 1 MiB ve bir kullanım senaryosunda yerel içerik okuma sınırı toplam 1 GiB'dir. Lock/busy beklemesi en çok 1 saniye ve toplam bütçenin içindedir. Boyut/bütçe aşımı açık yerel önkoşul hatasıdır; kısmi hash doğrulanmış sayılmaz. Bu ilk yerel bağlama politikasıdır, büyük veri/model aktarımının desteği veya fiziksel disk I/O için katı duvar saati garantisi değildir. 16 MiB/256 MiB/1 GiB sentetik dosyada hash belleğinin dosya boyutuyla büyümediği ve sınır/timeout retleri kabulde ölçülür.

Her `prepare`, `validate` ve `approve` güncel tipli doğrulama portunu kullanır. Producer portları composition katmanında seçilir; public caller capability/yetki/artefakt doğrulama nesnesi enjekte edemez. Uzak kritik karar yalnız TTL içindeki cache'e dayanmaz; aynı secret snapshot'ıyla güncel hesap/yetki doğrulaması gerekir. P01-3'te bu adaptörler yokken public plan açık engellerle `draft`, `executable=false` kalır. Gerçek destek olmadığı halde `prepared` sonucu üretilmez. Pozitif hazırlık/onay kabulü test fixture portlarıyla, ürün backend'i eklenmeden yapılır.

Validation kayıtlı seçimleri yeni profile göre değiştirmez; mevcut profil/hedef/yetki/girdiyle karşılaştırır. Gerekli bütün bağlar doğrulanmış/eşit/taze ve görev adaptörü mevcutsa hazırlık geçerli olabilir. Hedef/API kökü, hesap/proje, credential nesli, izin/kaynak sınırı, model içeriği/sürümü, executable/environment veya parametre değişimi geçersiz kılar. Salt profil adının aynı olması yeterli değildir. Producer yenilemesinde yalnız zaman ilerlemesi, aynı kapsam/semantik karar korunuyorsa eski planı değiştirmez; planın ilk expiry'si uzatılmaz. Kaynak/politika veya kararın anlamı değişmişse yeni plan gerekir.

Plan geçerliliği en çok 300 saniye ve bütün gerekli kanıt/girdi/tahmin bağlarının en erken expiry'si kadardır. Tam expiry/saat anomalisi veya ADR-0013'te kalıcılaştırılmış clock generation farkı geçersizdir. Saat watermark'a yetiştikten ve restart sonrasında da eski plan/onay canlanmaz. Validation sonucu yalnız o snapshot'ın kontrolüdür; daha sonra yeniden kullanılacak dispatch bileti değildir. Son kısa transaction'da etkin store/epoch/clock generation ve bütün credential ID/revision tekrar karşılaştırılır; çatışma `state_changed`, otomatik retry yoktur. Denetimden sonra env/profil tekrar çözülmez.

`executable`, bu kullanım senaryosunda her zaman false'tur: P01-3 hiçbir run/start/dispatch sağlamaz. Gelecekte `prepared` ve geçerli onay bile P01-4'ün operation/attempt/lease kaydı ve P01-5/P02/P03'ün yürütüm kapıları olmadan yan etki başlatamaz. Aynı dosyanın denetim sonrası haricî süreççe değiştirilmesini tüm gelecek süre boyunca engellediğimiz iddia edilmez; yürütücü kendi son doğrulama/snapshot sınırını ayrıca korur.

### Açık onay ve iptal

Onay plan gövdesindeki `approved=true` alanı değildir; ayrı yerel kayıttır. `plan_id`, schema sürümü, tam digest, store/epoch/clock generation, doğrulanan bağlar, açık onay zamanı ve en geç plan expiry'siyle ilişkilidir. `approve` güncel validation'ı tekrar yapmadan onay yazamaz. Onaylı plan değişmez; başka içerik yeni ID/digest ister.

CLI açık `--confirm PLAN_DIGEST`, Python açık `confirmation` argümanı ister; eksik/yanlış onay `approval_required` çıkış 4'tür. Prompt veya sessiz onay yoktur. Geçersiz/blocked plan `plan_not_valid` çıkış 2 ile reddedilir. Aynı hâlâ geçerli digest'in tekrar onayı aynı etkin kayıt sonucunu verir; bir yan etkiyi tekrar gönderme yetkisi değildir. `revoke` etkin onayı açıkça etkisizleştirir; sonraki onay yeniden validation ister. Onay kaydını sunmak veya bir modelin onay istediğini söylemek, kriptografik insan kimliği kanıtı değildir; UI/CI/MCP caller yetkilendirmesi ayrıca uygulanır.

Her plan için en çok bir güncel onay/iptal kaydı tutulur; tam insan denetim günlüğü iddia edilmez. Kayıt scheme/digest/store/epoch/tarih sınırları okuma ve yazmada denetlenir. Reset/restore yeni epoch açınca uzak ve local-only eski onaylar etkisiz kalır; otomatik yeniden onay yoktur.

### Kalıcılık ve açık yönetim

Plan/onay gerçek SQLite tüketicileriyle yeni immutable migration adımlarında eklenir; capability cache temizliği bunlara dokunmaz. Her plan gövdesi en çok 64 KiB ve 128 girdi bağı, store en çok 1.024 plan taşır; otomatik plan/onay silinmez. Kota dolduysa kontrollü `plan_capacity_exceeded` çıkış 2 ve açık yerel yönetim yolu gösterilir. Sıcak sorgu bütün geçmişi belleğe yüklemez.

Bu pakette bounded `list`, önceden ID bilinmeden kayıtlı planların ID/digest/görev/zaman/onay özetlerini bulmayı sağlar; varsayılan sayfa 50, üst sınır 100'dür. `(prepared_at, plan_id)` sıralı cursor sayfalaması kullanılır; payload veya sır okunmaz. Liste güncel execution validity iddia etmez; tarihsel/etkisizleşmiş planlar görünürdür. Bu plan kayıt yönetimidir, P01-4c'nin jobs/operation listesi değildir.

`forget`, seçili planı ve transaction anında ona bağlı güncel onayı aynı transaction'da, açık `--confirm PLAN_DIGEST` ile siler. Etkisi yalnız yerel kaydı unutmak olarak gösterilir; uzak işi iptal etmez. Yanlış digest veya değişmiş plan gövdesi reddedilir. Confirmation onayın önceki durumunu sabitlemez; arada onay/revoke değişmiş olsa da kullanıcının doğruladığı plan ve o andaki bağlı onay birlikte unutulur. İleride operation bağı varsa plan silme bu bağı aşamaz; P01-4 tüketicisi aynı transaction/FK sınırını kurmak zorundadır. Yalnız onay durumunu değiştiren `revoke`, plan içeriğini silmez. Tekrarlı revoke kontrollü/idempotent yerel sonuçtur.

### Restore ve recover: P01-3 genişlemesi

P01-3, **açıkça tanımlanmış identity + capability cache/clock + plan + approval** şema tüketicilerinde migration snapshot restore/recover desteğini sürdürür. Bu, ADR-0012'nin identity-only alt kümesini genişleten yeni karardır. Runtime kapısı pozitif allowlist'tir; bilinmeyen tüketici veya operation/attempt/lease/rezervasyon geçmişi olan runtime'da, kaynak eski/boş veya hedef eksik olsa dahi restore/recover reddedilir. ADR-0012'nin operation tüketicisinde kesin ret sınırı değişmez.

Restore yeni epoch/K kurar. Snapshot'taki planlar tarihsel olarak okunabilir, fakat eski geçerlilik/onay ve cache aktif olamaz; local-only kayıt da bundan muaftır diye yorumlanmaz. Reset canlı geçmişi korur, restore snapshot sonrası plan/onay geçmişini kaybedebilir. Kayıp geçmişin uzaktan geri getirildiği iddia edilmez.

Yeni bakım önizlemesi biçim sürümü 2 ile, identity özetine ek plan/onay sayısı ve sır içermeyen ID/digest/durum/zaman fingerprint'ini onaya bağlar; kullanıcıya kayıp/etkisizleşme kapsamını gösterir. Preview sonrası yalnız plan veya onay değişmişse confirmation stale olur. Yeniden üretilebilir cache/clock güncellemeleri bakım onayını tek başına bozmaz; cache'in etkisizleşeceği önizlemede açık yazılır. Fingerprint ham DB hash'i veya özel verifier içermez. Mevcut bakım komutları ve açık confirmation akışı korunur; v2 çıktı farkı CLI/state referansında belgelenir.

Kaynak/stage/live full validation şema sürümüne duyarlıdır. Önceki sürümden kalan restore intent'inde henüz stage yok, tamamlanmış eski stage var ve publish edilmiş eski live var senaryoları açık recover ile desteklenir. Tamamlanmış çiftte kaynak backup artık bulunmasa da intent'in ilan ettiği epoch/K korunarak gerekli migration/kalıcılık tamamlanır; hedef runtime şemasına ulaşılmadan intent kaldırılmaz. Eski stage/live shortcut'ı yeni tüketici doğrulamasını atlayamaz. Yeni epoch üretmek, bozuk payload'ı geçerli hale getirmez.

### Public yüzey

**Aşağıdakiler öneridir; henüz çalışan komut değildir.**

```text
yorunge plan execution prepare --task TASK [--recipe FILE] [--input-root PATH] [--state-dir PATH]
yorunge plan execution list [--limit N] [--cursor CURSOR] [--state-dir PATH]
yorunge plan execution show --plan-id ID [--state-dir PATH]
yorunge plan execution validate --plan-id ID [--config FILE] [--state-dir PATH]
yorunge plan execution approve --plan-id ID --confirm DIGEST [--state-dir PATH]
yorunge plan execution revoke --plan-id ID [--state-dir PATH]
yorunge plan execution forget --plan-id ID --confirm DIGEST [--state-dir PATH]
```

Python karşılıkları ayrı `prepare_execution_plan`, `list_execution_plans`, `show_execution_plan`, `validate_execution_plan`, `approve_execution_plan`, `revoke_execution_approval`, `forget_execution_plan` kullanım senaryolarıdır. Prepare mevcut seçim seçeneklerini, validate/approve güncel config/profile/project karşılaştırmasını kabul eder; list/show/revoke/forget seçimi değiştiren seçenek kabul etmez. Hepsi `Path`/strict girdi ve ortak tipli Result/YorungeError sınırını kullanır. `list`/`show` sır/girdi okumaz, validation yapıldı iddiası taşımaz; yapı doğrulaması güncel geçerlilik değildir. Validation sorgusu `valid=false` ve gerekçeleri normal raporlayabilir; bozuk istek/state kontrollü hatadır. Her yeni sonuçta `operation_id=null`; run veya sahte training başarısı yoktur.

## Değerlendirilen alternatifler

- **Offline Plan'ı yerinde prepared yapmak:** Eski dosyanın değişmez seçim ve dar kanıt sözleşmesini bozar; reddedildi.
- **JSON'daki onay veya digest'i tek yetki saymak:** Hash'i yeniden hesaplayan caller'a güven verir; provenance/validation yerine geçmez.
- **P01-3'te operation/run eklemek:** P01-4/5 ve gerçek adaptörlerin kabulünü gizler; eklenmez.
- **Restore'u ilk cache tablosunda kapatmak:** Önceki identity recover desteğini de keser. Yan etki geçmişi oluşmadan, bütün yeni yetkiyi epoch'la etkisizleştiren sınırlı genişleme seçildi; operation restore'u açılmaz.
- **Planları otomatik temizlemek veya sınırsız tutmak:** İlki audit/approval bağını gizlice kaybeder, ikincisi kaynak sınırı koymaz. Kota ve açık seçili forget tercih edildi.

## Sonuçlar

Onay ayrı execution v2 hazırlığını, güncel bağ doğrulamasını, açık digest onayını, yerel kayıt yönetimini ve P01-3 restore/preview uyumluluğunu kapsar. P01-3'te gerçek EVREN/araç adaptörü olmadığından public görevler non-executable/blocked kalabilir; bu sınır teslim eksikliği diye gizlenmez ve sahte destekle aşılmaz. [P01-3b kabulü](../roadmap/tasks/p01-3b-execution-plan-validity.md) ile bakım regresyonları tamamlanmadan epik kapanmaz.
