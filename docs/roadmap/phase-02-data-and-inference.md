# P02 — Veri, katalog ve çıkarım

**Durum:** Planlandı; satırlar uygulama kartı değildir. **Bağımlılık:** P01 kimlik/taşıma/state kabulü. **Yetenekler:** C03–C07, C11 okuma, C12 aktarım/teslim. Araştırma bağımsız ilerleyebilir; canlı yürütüm kapılıdır.

## Hatlar ve sınırlar

| ID | Teslim / ilk sınır | Önkoşul | Kabul kanıtı | Durum |
|---|---|---|---|---|
| P02-0 | Güncel sözleşme ve gerçek hesap bağlamı giriş hattı | P02-0a, P02-0b | Araştırma ile canlı kimlik keşfi ayrı kabul edilir | `draft` |
| P02-0a | Platform/LLM sözleşmesi, SDK kararı ve pilot planı | B03/B04; resmî kaynak | Auth/endpoint/envelope/limit/idempotency ve hesap/org/proje yüzeyi; belge ve hesap kanıtı ayrık | `draft` |
| P02-0b | Hesap/organizasyon/proje salt okunur keşfi ve context doğrulama | P02-0a, P01-2b, P01-3a, P01-5a | Doğru hizmet/anahtar, açık seçim; listede ilk UUID seçilmez, bilinmeyen yetki doğrulanmış sayılmaz | `draft` |
| P02-1 | Yerel normal dosya denetimi ve sürümlü manifest | P01-1 | Güncel hash, aynı boyutta değişim, kök/symlink ve duplicate; ağ/sır/eğitim yok | `draft` |
| P02-2 | Private oluşturma + tek doğrulanmış upload yolu | P02-0, P02-1, P01-4b, P01-5b | Presign/PUT/confirm, kayıp cevap ve unknown; public/ZIP gibi ek yollar ayrı paket | `draft` |
| P02-3 | Resume/reconcile, indirme, verify ve veri sürüm bağları | P02-2 | Stale günlük/uzak silinme, no-clobber, hash/metadata seviyesi ve sürüm değişimi | `draft` |
| P02-4 | Katalog/model keşfi ve sabit sürüm çözümü | P02-0, P01-3a, P01-5a | Sayfalama/cache, belirsiz slug, unknown model/görev ve yetki; eğitim yok | `draft` |
| P02-5 | Native LLM ve temel çıkarım | P02-4, P01-5b | Önce tek nonstream metin görevi; stream, embedding/rerank ve görsel ayrı alt paketler | `draft` |
| P02-6 | GPU/kuyruk/rezervasyon bilgisi ve kota okuma | P02-0, P01-3a, P01-5a | Gün/tarih/kapsam, paylaşılan kota ve yetki ayrımı; kaynak yazma yok | `draft` |

P02-1 yerel iş olarak P01'in kalan state/HTTP işlerinden bağımsız geliştirilebilir; bu, uzak upload'ı erkene alma izni değildir. P02-4/P02-6 okuma hattı upload/vision eğitimini beklemez. P02-0a araştırması yetkili canlı pilot olmadan tamamlanırsa yalnız belge/fixture uyumu kaydedilir; P02-0b'nin hesap kabulü tamamlandı sayılmaz. Organizasyon/proje alanı sağlayıcıda doğrulanmıyorsa uydurulmaz; mevcut dar context şemasının genişlemesi ayrıca sözleşme/migration farkıyla ele alınır.

## İşe başlamadan bölünecek paketler

- **P02-2 (L):** private oluşturma/plan; presign/PUT/confirm; hata/yeniden başlatma. Yeni kaynak oluşturan çağrı belirsizse tekrar create yapılmaz. İlk akış tek açık proje ve doğrulanmış dosya biçimiyle sınırlanır; limit uydurulmaz.
- **P02-3 (L):** uzlaştırma; akışlı güvenli indirme/verify; sürüm/bölme metadata'sı ve planın değişmez veri bağı. Sürüm oluşturma/freeze ayrıca etkili işlemdir.
- **P02-5 (L):** nonstream chat; terminal semantiği olan stream; embedding/rerank; keşfedilmiş görsel modelde predict. Her birinin girdi/çıktı sınırı ve hata modeli kartında belirlenir; tek PR'da hepsi istenmez.
- **P02-4 (M/L):** önce katalog/model sorgusu ve revision çözümü; seçilmiş ağırlık fetch'i P02-3'ün güvenli indirme/artefakt portunu kullanacak ayrı alt iş. Hesap/context sahipliği identity modülünde kalır.
- **P02-6 (M):** kamu GPU görünürlüğü, hesap tahsisi ve quota/ledger kaynağı ayrı etiketlenir. Kamu envanteri kullanıcının erişimi veya fatura garantisi değildir.

Bu alt ayrımlar iş yönünü tanımlar; henüz ready kart oluşturmaz. Aktif olacak alt pakete kararlı `a/b/...` ID, açık format/boyut/süre bütçesi, canonical referans ve sentetik fixture bağlanır. Endpoint/model/limit parametreleri güncel sözleşmeden alınır.

## Faz kabulü

Veri sorumlusu küçük sentetik klasörü doğru projede private veri setine aktarır, kesintiden sonra aynı operation üzerinden uzlaştırır ve geri indirip doğrular. Uygulama geliştirici desteklenen model/görevde native çıktı ve kullanım/hata bilgisini alır. Bu işler ForgeLM veya ML kurulumunu gerektirmez.

Offline contract/loopback testleri ile yetkili küçük pilot ayrı raporlanır. Aynı boyutta değişim, yanlış hizmet/kimlik, kesik PUT/SSE, 2xx mantıksal hata, 403/429 ve eksik dosya negatif kanıtı gerekir. [Aktarım RSS/worker/deadline bütçeleri](../standards/performance.md) gerçek veri boyutu ve donanımla ölçülür. İlk kullanıcı görevinde süre, yardım, yanlış seçim ve çıktı bulunabilirliği karttaki hedefe göre kaydedilir.

Public görünürlük, silme, rezervasyon yazma, görsel eğitim, OCR/ses ve notebook execution bu faza gizlenmez. Kapalı hizmet, boş liste veya sahte başarıya çevrilmez. Faz kapanışı C03–C07/C11'in kanıtlı alt kapsamını tek tek gösterir; bütün dış hizmetlerin desteklendiğini ilan etmez.
