# Yerel veri manifesti ve doğrulama

**Durum:** [ADR-0023](../decisions/0023-local-dataset-manifests.md) Accepted; public CLI/Python ve atomik yayın [PR #13](https://github.com/HodeTech/Yorunge/pull/13) / [50d68b1](https://github.com/HodeTech/Yorunge/commit/50d68b1deab80d6fe14749d556efde1f103b5759) ile development’a teslim edildi. Kod review, kurulum/native ve üç ortam CI/kalıcı kanıt kabulü [merge kaydında](../research/p02-1-implementation-validation.md#development-merge-kapanışı). **Güncellendi:** 2026-11-02. Bu belge implementasyonun kanonik sözleşmesidir; paket yayını veya Master/release kaydı değildir.

## Public yüzey

```text
yorunge datasets inspect ROOT --manifest-out FILE [--output text|json|ndjson] [--non-interactive]
yorunge datasets verify ROOT --manifest FILE [--output text|json|ndjson] [--non-interactive]
api.inspect_dataset(root: Path, *, manifest_out: Path) -> Result[DatasetInspection]
api.verify_dataset(root: Path, *, manifest: Path) -> Result[DatasetVerification]
```

Python dosya argümanları strict `Path`’tir; string/None/wrong type `invalid_request` olur. CLI root konumsal ve zorunludur; tekil seçenek tekrarları reddedilir. Config/profile/project/state-dir/recipe/task/tool/execution/refresh seçenekleri desteklenmez; ağ/env/SQLite okunmaz veya oluşturulmaz. Root ve artifact yolu CWD’ye çağrı başında bir kez bağlanır; mutlak argümanda CWD okuması gerekmez. `..` içeren yol reddedilir, symlink çözerek kabul/fallback yoktur. Mutlak root ve artifact yolu en çok 4.096 strict UTF-8 byte’tır. Her iki ankrajın bütün bileşenlerinde C0/C1 kontrol karakterleri, surrogate ve Unicode bidi override/isolate U+202A…U+202E/U+2066…U+2069 reddedilir. Artifact leaf adı da aşağıdaki göreli yol bileşeni yasaklarına uyar; parent bileşenleri bu ankraj güvenlik kuralına tabidir. Böylece kontrol karakteri JSON escaping’iyle özetin büyümesi veya terminal kontrolü taşınması kabul edilmez. Yayın öncesi tam DTO/Result JSON ve NDJSON result payload’ının UTF-8 encoded boyutu ayrıca ≤16 KiB olarak preflight edilir; aşımsa dataset_limit_exceeded/2 ve yayın yoktur. Platform/primitive destek kapısı, manifest okuma ve dizin taraması dahil bütün filesystem I/O’sundan öncedir; yalnız platform/capability sorgusudur. Normal iptal mevcut request_cancelled/6, BrokenPipe output_closed/6, renderer I/O output_write_failed/1 kuralını kullanır; publication sonrası belirsizlik aşağıda önceliklidir.

Inspect’in `--manifest-out` seçeneği zorunludur. Parent mevcut, root dışında ve no-follow olmalıdır. Verify manifesti de root dışındadır; manifest adı için otomatik ignore yapılmaz. Gizli dosyalar ve bütün alt dizinler taranır. Boş ağaç kabul edilir; boş dizinler içerik kimliğinde yoktur. İçeriğin veri/etiket formatı veya ML uygunluğu değerlendirilmez.

## Manifest v1

Tam root alanları: `schema_version`, `policy_version`, `kind`, `hash_algorithm`, `files`, `file_count`, `total_bytes`, `digest`. Başka veya eksik alan, duplicate key, UTF-8/JSON hatası, NaN/Infinity ve bilinmeyen sürüm reddedilir.

| Alan | Kesin tür ve kural |
|---|---|
| schema_version / policy_version | `type(value) is int`, ikisi de 1; bool/float değil |
| kind / hash_algorithm | Tam `dataset_manifest` / `sha256` |
| files | JSON array, en çok 4.096 kayıt; her kayıt tam `{path,size,sha256}` |
| path | Aşağıdaki göreli yol; orijinal ad, tekrarsız, UTF-8 byte sözlük sırası |
| size | Strict int, 0…1.073.741.824; bool/float değil |
| sha256 / digest | 64 lowercase ASCII hex |
| file_count | Strict int; tam `len(files)` |
| total_bytes | Strict int, 0…1.073.741.824; tam bütün size toplamı |

Digest, yalnız `digest` hariç bütün root alanlarının `json.dumps(ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)` UTF-8 baytlarının SHA-256’sıdır. Artifact aynı kodlamayla digest dahil üretilir ve tek LF ile biter; LF digest girdisi değildir. Parser başka anlamsız JSON whitespace’ini kabul edebilir, ancak dosya byte sınırı geçerlidir. Parser eksik sıralamayı düzeltmez, adı normalize etmez, digest’i kendiliğinden yeniden hesaplayıp kabul etmez. Root/yerel kimlik/zaman dosyada bulunmaz. Geçerli aynı dosya kümesini başka root’ta verify etmek desteklenir; bu provenance veya auth değildir.

Örnekte gerçek digest yerine yer tutucu vardır; geçerli fixture değildir:

```text
{"digest":"COMPUTED_SHA256","file_count":1,"files":[{"path":"images/a.bin","sha256":"CONTENT_SHA256","size":3}],"hash_algorithm":"sha256","kind":"dataset_manifest","policy_version":1,"schema_version":1,"total_bytes":3}
```

Strict parser en çok 8 MiB girdi okur; JSON container depth ≤8 ve node ≤50.000. Root object derinlik 1’dir; her object/array derinliği bir artırır, scalar artırmaz. Node her container, scalar ve object key için bir sayılır. Derinlik JSON parse öncesi string/escape farkındalıklı denetlenir; byte bütçesi parse allocation’ını sınırlar, node kontrolü tek başına parse öncesi bellek garantisi sayılmaz.

## Yol ve envanter politikası

Her path root’a göredir; `/` ayırıcıdır. Mutlak yol, boş/`.`/`..` bileşen, slash dışı separator ve traversal yoktur. Her bileşen 1…255, bütün yol 1…1.024 strict UTF-8 byte; en çok 32 bileşen. Surrogate, C0/C1 kontrolü, `<>:"\\|?*`, sondaki ASCII boşluk/nokta ve büyük/küçük harf duyarsız DOS aygıt gövdeleri (`CON`, `PRN`, `AUX`, `NUL`, `COM1`…`COM9`, `LPT1`…`LPT9`; ilk noktadan önceki gövde) reddedilir. Unicode bidi override/isolate karakterleri U+202A…U+202E ve U+2066…U+2069 kabul edilmez. Diğer geçerli Unicode adlar korunur.

Kardeş bileşen collision anahtarı `NFC(NFC(name).casefold())`’dur. Aynı key’e sahip farklı orijinal bileşenler, dosya/dizin olsa da reddedilir; `A/x` ile `a/y` bunun içindedir. Dosyanın başka path’in ancestor’ı olması da bozuk manifesttir (`a` ve `a/b`). Sadece tam dosya string’ini karşılaştırmak yeterli değildir. Python `unicodedata.unidata_version` değeri sonuçta `unicode_version` ile bildirilir; versiyonlar arası yeni ret olasılığı [ADR sınırındadır](../decisions/0023-local-dataset-manifests.md#içerik-kimliği-ve-adlar).

Dosya kimliği path’tir. Hardlink’ler ve aynı hash farklı adlar ayrı sayılır/hash’lenir; her biri mantıksal byte tavanını tüketir. Hardlink’in root dışındaki diğer adını araştırma garantisi yoktur. Symlink, FIFO/socket/device ve root’tan farklı device girdisi reddedilir. Dizin sayısı root dahil ≤4.096; dosya sayısı ≤4.096; metadata enumeration bunları aşarak sınırsız ad toplamaz. İzin/okuma hatası boş dosya/listesi sayılmaz.

No-follow root/ancestor/leaf, taze stat, hash öncesi/sonrası imza, son tüm dosya/dizin üyelik ve root zinciri denetimleri [ADR-0023](../decisions/0023-local-dataset-manifests.md#descriptor-üzerinden-tarama-ve-güncellik) ile zorunludur. Her file ≤1 GiB ve toplam mantıksal içerik ≤1 GiB; block ≤1 MiB; worker 1; scanner açık descriptor ≤64. Ağaç atomik snapshot değildir; gözlenen değişim `input_changed` olur. Upload veya execution bu raporu gelecekteki içerik izni sayamaz. Mevcut execution Plan v1/v2, recipe, 128 input ve 64 KiB body değişmez.

## Sonuçlar ve karşılaştırma

İki işlem aynı Result v1, `operation_id=null`, `status=completed`, `warnings=["local_files_only"]` kullanır. Bütün sonuç DTO’ları strict/frozen/extra-forbid’dır; çıktı scalar/özetlidir ve 16 KiB’ı geçmez. Tam `files` listesi stdout’a veya NDJSON event’ine eklenmez.

Text sonucu manifest yolunu, digest/sayıları ve sonraki verify adımını gösterir. Tam shell-quoted komut uzun ankrajlarla 16 KiB’ı aşacaksa yollar kesilmez; sonraki adım `yorunge datasets verify ROOT --manifest FILE` olarak, ROOT’un aynı kaynak ve FILE’ın gösterilen manifest olduğu açıklamasıyla verilir. JSON/NDJSON sonucu bu sunum tercihinden etkilenmez.

`DatasetInspection` tam alanları: `schema_version=1`, `manifest_path` (çağrıda bir kez bağlanmış mutlak hedef), `manifest_digest`, `file_count`, `total_bytes`, `unicode_version`. Başarı yalnız atomik yayın/kalıcılık sonrasında döner. Manifest artifact’ı PII/özel ad/hash taşıyabilir; 0600 oluşturulur. Sır/env çözülmediğinden genel secret veya PII sınıflandırması iddia edilmez; dosya adları bilinçli artifact girdisidir.

`DatasetVerification` tam alanları: `schema_version=1`, `manifest_digest`, `file_count`, `total_bytes`, `matches=true`, `unicode_version`. Verify kaynak manifestini parent zinciri ve leaf dahil no-follow/nonblocking descriptor ile açar, regular fstat zorunludur; ilk gözlenen boyut ≤8 MiB olmalıdır. Bounded okuma öncesi/sonrası fstat ve tekrar açılmış path zinciri/kimliği karşılaştırılır; kısa okuma/değişim input_changed, özel/symlink girdi input_invalid, başlangıç I/O’su file_unreadable olur. Sonra strict parse/digest denetler; ardından root’u tamamen tarar. Son metadata geçişi içerikleri ikinci kez hash’lemez; her dosyanın device/inode/mode/size/mtime_ns/ctime_ns imzasını, dizin üyeliğini ve kök zincirini ilk hash gözlemiyle yeniden karşılaştırır. Eşitlik sıralı `(path,size,sha256)` kümesidir. Dosya adı eksik/fazla veya boyut/hash farklıysa `manifest_mismatch` oluşur; boş dizin farkı mismatch değildir. Yeni tarama manifesti otomatik diske yazılmaz.

`ManifestMismatch` mevcut YorungeError zarfına yalnız şu kapalı details’i ekler: `expected_digest`, `actual_digest`, `missing_file_count`, `unexpected_file_count`, `changed_file_count`. İlk iki alan lowercase SHA-256, sayaçlar strict nonnegative int ≤4.096’dır. Missing/unexpected yalnız path kümesi farkıdır; changed ortak path’te size veya sha256 farkıdır. Ham path listesi, root veya içerik hata zarfına girmez. Kullanıcı farklı yeni bir hedefe inspect yapıp iki dosyayı ayrıca inceleyebilir; eski manifest ezilmez. Verify uyuşmazlıkta completed Result üretmez, JSON stdout boştur ve tek hata stderr’dir; NDJSON ilk publish öncesi aynı kuralı izler.

## Dosya yayını ve hata önceliği

Kaynak ağacı/çıktı parent’ı descriptor zincirleriyle sabitlenir. Parent’ın root veya altı olduğu kimlik zinciriyle de reddedilir; salt metin prefix’i yeterli değildir. Parent ayrı bir symlink alias’ıyla root içine açılmaz. Stage aynı parent’ta rastgele tek adla `O_EXCL|O_NOFOLLOW`, 0600 açılır; serializasyon tam ve bounded’dir. File sync ve gerekli platform full-sync, son parent/root zinciri kontrolü ardından aynı directory’de exclusive `link` ile yeni hedef yayınlanır. Stage unlink ve parent sync tamamlanır; hedefe overwrite/replace yapılmaz. Son hedef descriptor/inode eşliği ve parent zinciri denetlenir. Desteklenmeyen primitive hata yutma veya overwrite fallback’i açmaz.

Toplam deadline çağrı başlangıcından parse/scan/serialize/publish’e kadar 30 s’tir; her sınırlı iş/okuma ve yayın öncesi/sonrası kontrol edilir. Verify manifest okuması içerik toplamından ayrı ≤8 MiB’dir. Metadata/name/JSON sınırları kendi boyutlarıyla işler. Kernel I/O’sunu zorla durdurma veya fiziksel disk süresi garantisi yoktur.

| Kod | Exit | Tetik |
|---|---:|---|
| invalid_request | 2 | Argüman türü/tekrarı, eksik output, desteklenmeyen context seçeneği |
| input_unsupported | 2 | macOS/Linux veya zorunlu descriptor/primitive desteği yok |
| input_invalid | 2 | Root/path politikası, symlink/özel dosya/device/isim çakışması veya kaynak/artifact konumu geçersiz |
| input_changed | 2 | Hash/tarama sırasında gözlenen içerik/path/root/dizin üyelik değişimi |
| input_budget_exceeded | 2 | 1 GiB mantıksal içerik sınırı; mevcut P01 mesaj anlamı korunur |
| dataset_limit_exceeded | 2 | Dosya/dizin/ad/derinlik/manifest çıktı kapasitesi tavanı |
| dataset_timeout | 2 | Yerel inspect/verify monotonic 30 s bütçesi doldu; execution_timeout mesajı yeniden kullanılmaz |
| manifest_invalid | 2 | Girdi manifestinin strict JSON/şema/sıra/digest/toplam/8 MiB/depth/node doğrulaması geçmiyor |
| file_unreadable | 2 | Başlangıç erişimi veya yerel read I/O’su yapılamıyor; ham OSError/path yok |
| manifest_output_exists | 2 | Hedef zaten mevcut veya publication yarışında başkası oluşturdu; eski hedef korunur |
| manifest_write_failed | 2 | Publication öncesi stage/write/sync/çıktı I/O hatası |
| manifest_write_uncertain | 5 | Kritik publication çağrısının sonucu bilinmiyor veya final kalıcılık/cleanup/son kontrol bitmeden hata/iptal/deadline; hedef oluşmuş olabilir, otomatik tekrar yok |
| manifest_mismatch | 7 | Geçerli manifest ile tamamlanmış güncel tarama eşleşmiyor; kapalı sayı/digest ayrıntısı |

Girdi manifesti malformed ise tarama veya output oluşturulmaz. Tarama değişim/okuma/bütçe hatası, tamamlanmış içerik karşılaştırmasına tercih edilir; bozuk/yarım tarama mismatch değildir. Kritik link çağrısının başlamasından önceki iptal cleanup sonrası mevcut request_cancelled/6 yoludur ve bu çağrı hedef yaratmamıştır. Link çağrısı başlamış fakat sonuç kesinleşmemişse, gerçek link hedefi oluşturduktan sonra dönüşte KeyboardInterrupt yükselse bile manifest_write_uncertain/5 önceliklidir; kesin EEXIST ayrı manifest_output_exists/2 olur. Başarılı link sonrasında final kalıcılık/cleanup/zincir kontrolleri bitene kadar hata da uncertain/5’tir. Bütün bu kontroller tamamlanıp API başarılı döndükten sonraki renderer BrokenPipe/I/O hatası output_closed/6 veya output_write_failed/1, sonraki SIGINT request_cancelled/6 olarak kalır; dayanıklı artifact geri alınmaz veya belirsiz yapılmaz. Önceden belirlenmiş gerçek manifest_write_uncertain sonucunun exit 5 önceliği korunur; normal close kendiliğinden cancellation üretmez. SIGKILL cleanup garantisi değildir; kalan stage/target otomatik silinmez. Genel envelope retryable=false; operation_id=null kalır. Ayrıntı eklenen tek yeni hata ManifestMismatch’tir; diğerleri details={} kullanır.

## Bağımsız kabul

Golden vektörler elle sabit dosya baytları ve bağımsız beklenen SHA/canonical manifest byte/digest kullanır; üreticinin kendi çıktısını tek oracle yapmaz. Boş dosya/ağaç, Unicode, farklı root/sıra, same-hash ve hardlink isimleri korunur. Parser, tüm quota ve adversarial yarışlar, disk-full/kill/existing target ve API/CLI JSON/NDJSON/locale/pipe negatifleri [kartlara](../roadmap/p02-1-delivery-plan.md) dağılır. Uygulanmış kapsam, çalıştırılan kontroller ve kabul sınırları [güncel development merge/CI kaydında](../research/p02-1-implementation-validation.md#development-merge-kapanışı) kaynaklarıyla belirtilir.

## Senkron API ve iptal ayrımı

Dataset API senkrondur; async dataset entry point, async generator veya thread iptal protokolü sunulmaz. Event loop içinde doğrudan çağrı loop’u bloklar; `Task.cancel()` senkron taramayı kesen bir deadline değildir. `asyncio.to_thread` await’inin iptali çalışan thread’i durdurmaz; çağıran tamamlanmayı/istenen hedefi ayrıca gözlemlemeden yeniden yayın denemesi yapmamalıdır. Bu davranış iptal edilmiş await’in thread’deki dosya yazısını rollback ettiği iddiası değildir.

Senkron API/CLI gerçek `KeyboardInterrupt` için mevcut CLI sınırını korur: kritik link başlamadan cleanup sonrası iptal yayılır ve CLI request_cancelled/6 üretir; link sonucu bilinmiyorsa veya final dayanıklılık kontrolleri bitmediyse manifest_write_uncertain/5 olur. Dayanıklı API başarı dönüşünden sonraki renderer I/O/SIGINT mevcut 6/1/6 anlamını korur.

Bir hook/alt çağrı gerçek `asyncio.CancelledError` yükseltirse descriptor’lar kapatılır, kimliği bilinen stage için cleanup denenir ve aynı istisna yeniden yükseltilir; YorungeError’a çevrilmez. Kritik link denemesi başlamışsa istisnaya yalnız sabit `MESSAGES["manifest_write_uncertain"]` note’u eklenir. Note ham path/değer taşımaz; caller seçtiği hedefi inceleyip sonucu öğrenebilir. Yayın başlamamışsa bu note eklenmez. Cleanup’ın kendi I/O hatası gerçek CancelledError’ı yutamaz. Bu negatif kabul gerçek Task.cancel yayılımı ile enjekte edilen publication istisnasını ayrı test eder; async destek veya thread’in zorla durdurulduğu iddia edilmez. ADR-0018 değişmez.

Ortak input_invalid/input_changed/input_unsupported mesajları execution planı hazırlamayan kullanıcıyı yeni plan oluşturmaya yönlendirmez; hem dataset hem execution bağlamında geçerli yerel dosya/kök denetimi ve sonraki adımı söyler. Makine kodu/exit korunur; text/JSON/NDJSON mesajları da regression kapsamındadır. CLI referansında bu hata tablosu kopyalanmaz, buraya bağlantı verilir.

Stage’in ilk fstat/kimlik okuması hata veya iptal verirse inode kimliği bilinmez; dosya adı üzerinden güvenli unlink kanıtlanamadığından boş 0600 stage kalabilir. Cleanup I/O’su veya SIGKILL de stage bırakabilir. Bu adlar startup’ta otomatik silinmez; kimliği bilinmeyen başka bir dosyayı silmek yerine hata/iptal korunur. İlk kimlik okumasındaki bu ret kritik link öncesidir; bu çağrının hedefi oluşmamıştır, uncertainty note’u eklenmez.
