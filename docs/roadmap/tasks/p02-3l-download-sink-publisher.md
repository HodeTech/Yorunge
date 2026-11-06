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

Parent zincirinin no-follow doğrulanması; hedef denetimi (hedef varsa `download_output_exists`; hedefle aynı inode’lu `nlink==2` artık stage için stage→sidecar silme) ve kapalı sıra: stage `lstat` → yoksa `O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR` 0600 + `fchmod(0600)` (umask’tan bağımsız; `EEXIST` yarışı mevcut-stage koluna döner), varsa `lstat` denetimi + `O_RDWR|O_NOFOLLOW|O_NONBLOCK` açılışı + fstat yeniden denetimi (uid/mod/`nlink`/normal dosya ve `lstat` kimlik eşleşmesi); ardından `flock(LOCK_EX|LOCK_NB)` (meşgul → `download_busy`) ve **kilit alındıktan sonra** sidecar/tmp okuma, silme ve stage kesme (ön ek aynı fd’den okunur, `ftruncate` aynı fd’de; `ENOENT` tolere edilir); sahiplik denetimi (normal dosya, uid, 0600, `nlink==1`, sidecar eşleşmesi); async görev içinde ≤1 MiB bloklarla yazma, artımlı SHA-256/bayt sayacı/tavan, deadline noktaları; sidecar protokolü (kabul edilen başlıklardan sonra ve ilk gövde baytından önce **başlık checkpoint’i**, atomik tmp+fsync+replace+dizin fsync, 8 MiB checkpoint’te önce `os.fsync`, `prefix_sha256` = hash `copy()` ile tam fsync edilen baytların özeti, gövde bitince **tamamlanma checkpoint’i**); başlangıç durum tablosu (boş stage yeniden kullanımı, kalıntı tmp, `download_partial_unverified`, `--no-resume` kolları); sabit silme sırası stage→sidecar→tmp→dizin fsync; kesin EEXIST’te ve beklenti uyuşmazlığında sahipliği kanıtlı stage/sidecar temizliği; resume doğrulama ilkelleri; tamamlanınca `full_sync`–link–unlink–dizin fsync–kimlik kontrolü yayını (P02-3s ortak ilkesiyle; yayın adımları deadline’dan muaf) ve bilinen kimlikle temizlik girer. HTTP, engine ve tüketici girmez.

## Bağımlılıklar ve kararlar

P02-3j tiplerine bağlıdır. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md)’nin Accepted olması gerekir (bugün Proposed). Manifest yayıncısı kalıbı kopyalanmaz: ortak yayın ilkesi P02-3s’te çıkarılmıştır ve manifest davranışı değişmez.

## Sözleşme ve uygulama sınırı

Yazıcı DatasetTree/30 s bütçeye bağlı değildir; hedef açık verilen yeni bir dosya adıdır, stage adı hedef adının sabit uzunluklu özetinden türer, kalıcı durum yalnız sidecar’dır. Link çağrısı başladıktan sonraki her belirsizlik `download_write_uncertain`dir ve otomatik tekrar yoktur; stage/parent kimliği yayın öncesi değişirse `download_write_failed`dır. Sahipliği kanıtlanmayan hiçbir dosya silinmez; hata mesajları sabittir (dosya adı yok). Stage SIGKILL ve disk hatasında kalabilir; otomatik silinmez (yalnız bilinen kimlikle kendi temizliği ve `--no-resume` siler). Dosya modu 0600’dür.

## Kabul

1. Hedef yarışları: hedef önceden var (dosya, dizin, kırık symlink), yayın yarışında oluşur, parent değiştirilir/symlink olur, stage adı ikame edilir (FIFO/aygıt düğümü dahil: `O_NONBLOCK` + `lstat` nedeniyle bloke etmez ve yazılmaz), yabancı uid’li stage, `nlink>1` stage, `O_EXCL` yaratma yarışı (`EEXIST` → mevcut-stage kolu), `umask 0277` (stage yine 0600 ve sonraki koşuda kabul edilir); hiçbirinde mevcut içerik ezilmez, kimliği kanıtlanmamış dosya silinmez ve yanlış başarı yoktur.
2. İki süreç aynı hedefe: ikincisi `flock` nedeniyle `download_busy` alır ve hiçbir dosyaya (tmp/sidecar dahil) dokunmaz; kilit alınmadan sidecar/tmp silme veya stage kesme hiçbir yolda yapılmaz (sıralama testi); yayın bozulmaz.
3. Stage/sidecar durumları: boş stage + sidecar yok (yeniden kullanım), dolu stage + sidecar yok (`download_partial_unverified`), sidecar var + stage yok (sidecar atılır), kalıntı sidecar tmp (sahiplik ✓ silinir / ✗ `download_partial_unverified`), bozuk sidecar, sahiplik ✗, kesin EEXIST sonrası stage/sidecar temizliği, dolu stage + sidecar yok için `--no-resume` (stage silinir) ve sahiplik ✗ için `--no-resume` (dokunmaz), hedefle aynı inode’lu `nlink==2` artık stage (stage→sidecar silinir, `download_output_exists`); tablo satırlarının hepsi.
4. ENOSPC/kısa yazma/uzun yazma enjeksiyonu: yayın yok, sidecar tutarlı, resume için koşullar doğru; yanlış boyutta yayın yok.
5. Gerçek SIGKILL kapalı sıranın her adımında (stage yaratma, `fchmod`, kilit, tmp yazma/replace, başlık checkpoint’i, veri yazma, checkpoint, tamamlanma checkpoint’i, `full_sync`, link öncesi/sonrası, stage/sidecar/tmp unlink’lerinin her biri, dizin sync) sonrası durum kapalı beklentilerle doğrulanır; **sonraki koşu elle silme gerektirmeden çözülür** (kalıcı `download_partial_unverified` takılması yoktur: silme sırası stage→sidecar→tmp olduğundan en kötü iz “stage yok, sidecar var”dır ve atılır); hedef ya yok ya tam ve doğru kimlikte.
6. Sidecar yalnız fsync edilmiş bayt sayısını iddia eder; `prefix_sha256` yerel bozulmayı yakalar; kısa/uzun stage, kimlik farkı ve bozuk sidecar resume’u reddeder; yarım içerik asla sessizce birleşmez. Başlık checkpoint’i sayesinde 8 MiB’tan küçük ilerleme de güçlü ETag’le devam eder; tamamlanma checkpoint’inden sonra deadline/I-O hatası stage’i atmaz (sonraki koşu tam-stage satırıyla yayımlar). Beklenti uyuşmazlığı stage ve sidecar’ı siler (ağsız exit-7 döngüsü yok).
7. SHA-256 bağımsız hashlib oracle’ıyla eşleşir; sınırı aşan yazma durdurulur; ≤1 MiB blok ve bloklar arası iptal/deadline kontrolü; Unicode ve uzun ad güvenli; checkpoint `os.fsync` ve yayın `full_sync` sürelerinin kaydı P02-3o kanıtı içindir.
8. Hata mesajları sabittir (dosya adı, yol, URL yok); manifest yayıncısının mevcut testleri değiştirilmeden geçer (P02-3s kanca sözleşmesiyle).

## Doğrulama

Gerçek dosya sistemi, fork/SIGKILL ve race integration testleri, Ruff, strict mypy. Büyük dosya bellek/süre ölçümü P02-3o’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
