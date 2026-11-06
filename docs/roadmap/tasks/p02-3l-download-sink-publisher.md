---
id: P02-3l
phase: P02
status: draft
size: M
depends_on: [P02-3j, P02-3s]
capabilities: [C03]
---
# P02-3l — Akışlı yerel yazıcı, sidecar protokolü ve resume doğrulaması

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 11. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) §3–§4; manifest yayıncısı kalıbının büyük dosya genellemesi ve P02-3q’nun da kullanacağı yayın adımı [P02-3s](p02-3s-common-artifact-publisher.md)’in ortak ilkesini kullanır. Büyüme kuralı: ölçülen büyüklük kartı L yaparsa iş sessizce küçültülmez; s–z harfleriyle (örn. yazıcı/race ve sidecar/resume) bölünür ve planda kaydedilir.

## Kullanıcı sonucu ve mevcut eksik

Mevcut tek yayıncı 8 MiB’lık bellekteki manifest içindir. Yüzlerce MiB’lık bir indirmeyi bellekte tutmadan, artımlı hash’leyerek, çökmeye dayanıklı ve hedefi ezmeden yayınlayacak yerel bileşen yoktur; ayrıca deterministik stage adı sahiplik ve eşzamanlılık protokolü gerektirir.

## Giren ve girmeyen kapsam

[Kapalı sıra](../../reference/download-engine.md#stage-ve-sidecar-protokolü) girer: parent zincirinin no-follow doğrulanması; hedef başına **kararlı kilit nesnesi** (`.lock`: `O_NOFOLLOW`, 0600, `flock(LOCK_EX|LOCK_NB)`, kilit sonrası fstat–lstat kimlik doğrulaması ve en çok üç yeniden deneme, her çıkışta kilit altında ve en son silme); **kilit altında** hedef denetimi (hedef varsa `download_output_exists`; hedefle aynı inode’lu `nlink==2` artık stage için stage→sidecar→tmp silme), stage `lstat` → `O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR` 0600 + `fchmod(0600)` veya sahiplik denetimi + `O_RDWR|O_NOFOLLOW|O_NONBLOCK` açılışı + fstat yeniden denetimi; ön ek aynı fd’den okunur, `ftruncate` aynı fd’de; sidecar sahipliği stage’den bağımsız (normal dosya, uid, 0600, `nlink==1`, ≤4 KiB, şema) ve stage varsa device/inode eşleşmesi; async görev içinde ≤1 MiB bloklarla yazma, artımlı SHA-256/bayt sayacı/tavan, deadline noktaları; sidecar protokolü (kabul edilen başlıklardan sonra ve ilk gövde baytından önce **başlık checkpoint’i**, atomik tmp+fsync+replace+dizin fsync, 8 MiB checkpoint’te ve **temiz durmada** önce `os.fsync`, `prefix_sha256` = hash `copy()` ile tam fsync edilen baytların özeti, gövde bitince **tamamlanma checkpoint’i** — chunked gövdede `total_size` burada sabitlenir); başlangıç durum tablosu; sabit silme sırası stage→sidecar→tmp→dizin fsync; kesin EEXIST’te ve beklenti uyuşmazlığında temizlik; `--no-resume` kolları; tamamlanınca `full_sync`–link–unlink–dizin fsync–kimlik kontrolü yayını (P02-3s ortak ilkesiyle; yayın adımları deadline’dan muaf) girer. HTTP, engine ve tüketici girmez.

## Bağımlılıklar ve kararlar

P02-3j tiplerine bağlıdır. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) Accepted’dir (2026-11-06). Manifest yayıncısı kalıbı kopyalanmaz: ortak yayın ilkesi P02-3s’te çıkarılmıştır ve manifest davranışı değişmez.

## Sözleşme ve uygulama sınırı

Yazıcı DatasetTree/30 s bütçeye bağlı değildir; hedef açık verilen yeni bir dosya adıdır, kilit/stage/sidecar/tmp adları hedef adının sabit uzunluklu özetinden türer, kalıcı durum yalnız sidecar’dır. Kilit stage’e değil kilit nesnesine bağlıdır; kilit alınmadan hiçbir dosya silinmez, kesilmez veya yeniden yazılmaz. Link çağrısı başladıktan sonraki her belirsizlik `download_write_uncertain`dir ve otomatik tekrar yoktur; stage/parent kimliği yayın öncesi değişirse `download_write_failed`dır. Sahipliği kanıtlanmayan hiçbir dosya silinmez; hata mesajları sabittir (dosya adı yok). Stage SIGKILL ve disk hatasında kalabilir; otomatik silinmez (yalnız bilinen kimlikle kendi temizliği ve `--no-resume` siler). Dosya modu 0600’dür.

## Kabul

1. Hedef yarışları: hedef önceden var (dosya, dizin, kırık symlink), yayın yarışında oluşur, parent değiştirilir/symlink olur, stage adı ikame edilir (FIFO/aygıt düğümü dahil: `O_NONBLOCK` + `lstat` nedeniyle bloke etmez ve yazılmaz), yabancı uid’li stage, `nlink>1` stage, yabancı/FIFO kilit nesnesi, `O_EXCL` yaratma yarışı, `umask 0277` (stage ve kilit nesnesi yine 0600 ve sonraki koşuda kabul edilir); hiçbirinde mevcut içerik ezilmez, kimliği kanıtlanmamış dosya silinmez ve yanlış başarı yoktur.
2. **Tek yazıcı:** iki süreç aynı hedefe: ikincisi `download_busy` alır ve hiçbir dosyaya (tmp/sidecar dahil) dokunmaz; kilit alınmadan sidecar/tmp silme, stage kesme veya hedef-artık temizliği hiçbir yolda yapılmaz (sıralama testi). Özel senaryolar: (a) kilit sahibi çalışırken atma/sıfırlama yolu stage’i silip yeniden yaratır — ikinci süreç farklı bir inode üzerinde kilit alıp yazamaz (kilit nesnesi sabit); (b) link sonrası canlı cleanup — birinci süreç `link()` yapmış ve temizlik yapmaktayken ikinci süreç artık stage’i silemez; (c) eski kilit fd’sini bekleten ikinci süreç, birincinin kilit nesnesini silmesinden sonra kilidi alırsa fstat–lstat uyuşmazlığıyla yeniden dener ve yeni nesneyi kilitler.
3. Stage/sidecar durumları: boş stage + sidecar yok (yeniden kullanım), dolu stage + sidecar yok (`download_partial_unverified`), sidecar var + stage yok (sidecar sahipliği ✓ atılır / ✗ `download_partial_unverified`), kalıntı sidecar tmp (sahiplik ✓ silinir / ✗ `download_partial_unverified`), bozuk sidecar, sahiplik ✗, kesin EEXIST sonrası stage/sidecar temizliği, dolu stage + sidecar yok için `--no-resume` (stage silinir) ve sahiplik ✗ için `--no-resume` (dokunmaz), hedefle aynı inode’lu `nlink==2` artık stage (stage→sidecar silinir, `download_output_exists`); tablo satırlarının hepsi.
4. ENOSPC/kısa yazma/uzun yazma enjeksiyonu: yayın yok, sidecar tutarlı, resume için koşullar doğru; yanlış boyutta yayın yok.
5. Gerçek SIGKILL kapalı sıranın her adımında (kilit nesnesi yaratma, `fchmod`, kilit, stage yaratma, tmp yazma/replace, başlık checkpoint’i, veri yazma, checkpoint, temiz durma checkpoint’i, tamamlanma checkpoint’i, `full_sync`, link öncesi/sonrası, stage/sidecar/tmp/kilit unlink’lerinin her biri, dizin sync) sonrası durum kapalı beklentilerle doğrulanır; **sonraki koşu elle silme gerektirmeden çözülür** (kalıcı `download_partial_unverified` takılması yoktur; kilit nesnesi boş artık olarak yeniden kullanılır); hedef ya yok ya tam ve doğru kimlikte. Chunked gövde için tamamlanma checkpoint’i, link ve cleanup sınırlarındaki kesintiler dahildir (tam chunked stage sonraki koşuda ağsız yayımlanır).
6. Sidecar yalnız fsync edilmiş bayt sayısını iddia eder; `prefix_sha256` yerel bozulmayı yakalar; kısa/uzun stage, kimlik farkı (hizmet hedefi dahil) ve bozuk sidecar resume’u reddeder; yarım içerik asla sessizce birleşmez. Başlık checkpoint’i güçlü ETag’i ve toplamı kaydeder; SIGKILL’de son checkpoint’ten sonraki baytlar (ilk 8 MiB’ta tüm ilerleme) yeniden indirilir ve bu belgelidir; temiz durmada (SIGINT, Task iptali, taşıma/zaman aşımı hatası) durma anındaki ilerleme checkpoint’lenir ve 8 MiB’tan küçük ilerleme de devam eder. Tamamlanma checkpoint’inden sonra deadline/I-O hatası stage’i atmaz (sonraki koşu tam-stage satırıyla yayımlar). Beklenti uyuşmazlığı stage ve sidecar’ı siler (ağsız exit-7 döngüsü yok).
7. SHA-256 bağımsız hashlib oracle’ıyla eşleşir; sınırı aşan yazma durdurulur; ≤1 MiB blok ve bloklar arası iptal/deadline kontrolü; Unicode ve uzun ad güvenli; checkpoint `os.fsync` ve yayın `full_sync` sürelerinin kaydı P02-3o kanıtı içindir.
8. Hata mesajları sabittir (dosya adı, yol, URL yok); manifest yayıncısının mevcut testleri değiştirilmeden geçer (P02-3s kanca sözleşmesiyle).

## Doğrulama

Gerçek dosya sistemi, fork/SIGKILL ve race integration testleri, Ruff, strict mypy. Büyük dosya bellek/süre ölçümü P02-3o’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
