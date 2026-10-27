# P02 — Veri, katalog ve çıkarım

**Durum:** Planlandı. **Bağımlılık:** P01. **Yetenekler:** C03–C07, C11 okuma, C12 aktarım/teslim.

| İş | Kapsam | Kabul |
|---|---|---|
| P02-1 | Yerel denetim ve sürümlü manifest | Güncel hash, kök/symlink, duplicate ve değişen dosya senaryoları |
| P02-2 | Private oluşturma ve presign/PUT/confirm | Doğru hedef/kimlik, mantıksal başarı, kesinti ve unknown davranışı |
| P02-3 | Resume/reconcile, indirme ve verify | Stale journal ve eksik uzak dosya; no-clobber ve teslim doğruluğu |
| P02-4 | Katalog/model sürümü ve görev keşfi | Sayfalama/cache, bilinmeyen tür ve hesap kapsamı |
| P02-5 | LLM metin/akış, embedding/rerank ve temel çıkarım | Model uyumu, 429/bozuk/kesik yanıt, bounded veri/süre |
| P02-6 | GPU/kuyruk/kota salt okunur görünüm | Dinamik zaman/kapsam, paylaşılan kota ve erişim ayrımı |

## Kullanıcı kanıtı

Bir veri sorumlusu klasörü yükleyip doğrular ve geri indirir. Bir uygulama geliştirici desteklenen modelde çıktı üretir, kullanım/hata bilgisini anlar. Bu işler için eğitim ortamı/ForgeLM kurulumu gerekmez. Güncel API sözleşmesi gerçek yetkili küçük pilotla ayrıca doğrulanır; normal CI sentetik kalır.

## Çıkış kapısı

Yanlış başarı veya gizli ikinci kaynak oluşturma yoktur. 1 GiB aktarım bellek sınırı ve listeleme/izleme çağrı sayısı ölçülür. Public görünürlük, silme veya kaynak rezervasyonu normal veri yükleme sonucuna gizlenmez. Ana akışlarda görev süresi, yardım ihtiyacı ve çıktı bulunabilirliği kullanıcı gözlemiyle kaydedilir.

İleri OCR/ses, tam görsel etiketleme editörü ve notebook execution bu fazın önkoşulu değildir. Doğrulanmayan servis görevleri capability'de açık kalır.
