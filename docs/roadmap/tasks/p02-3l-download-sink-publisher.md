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

Parent zincirinin no-follow doğrulanması; açılış öncesi `lstat` denetimi ve `O_NONBLOCK|O_NOFOLLOW` açılış (stage ilk koşuda `O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR` 0600, devam için `O_RDWR|O_NOFOLLOW|O_NONBLOCK`; ön ek aynı fd’den okunur, `ftruncate` aynı fd’de) ve `flock(LOCK_EX|LOCK_NB)`; sahiplik denetimi (normal dosya, uid, 0600, `nlink==1`, sidecar eşleşmesi); async görev içinde ≤1 MiB bloklarla yazma, artımlı SHA-256/bayt sayacı/tavan, deadline noktaları; sidecar protokolü (stage açılır açılmaz `committed_bytes=0`, atomik tmp+fsync+replace+dizin fsync, 8 MiB checkpoint’te önce `os.fsync`, `prefix_sha256` = hash `copy()` ile tam fsync edilen baytların özeti); başlangıç durum tablosu (boş stage yeniden kullanımı, kalıntı tmp, `download_partial_unverified`); kesin EEXIST’te sahipliği kanıtlı stage/sidecar temizliği; resume doğrulama ilkelleri; `--no-resume` silme politikası (yalnız sahipliği kanıtlı dosyalar); tamamlanınca `full_sync`–link–unlink–dizin fsync–kimlik kontrolü yayını (P02-3s ortak ilkesiyle) ve bilinen kimlikle temizlik girer. HTTP, engine ve tüketici girmez.

## Bağımlılıklar ve kararlar

P02-3j tiplerine bağlıdır. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md)’nin Accepted olması gerekir (bugün Proposed). Manifest yayıncısı kalıbı kopyalanmaz: ortak yayın ilkesi P02-3s’te çıkarılmıştır ve manifest davranışı değişmez.

## Sözleşme ve uygulama sınırı

Yazıcı DatasetTree/30 s bütçeye bağlı değildir; hedef açık verilen yeni bir dosya adıdır, stage adı hedef adının sabit uzunluklu özetinden türer, kalıcı durum yalnız sidecar’dır. Link çağrısı başladıktan sonraki her belirsizlik `download_write_uncertain`dir ve otomatik tekrar yoktur. Sahipliği kanıtlanmayan hiçbir dosya silinmez. Stage SIGKILL ve disk hatasında kalabilir; otomatik silinmez. Dosya modu 0600’dür.

## Kabul

1. Hedef yarışları: hedef önceden var (dosya, dizin, kırık symlink), yayın yarışında oluşur, parent değiştirilir/symlink olur, stage adı ikame edilir (FIFO/aygıt düğümü dahil: `O_NONBLOCK` + `lstat` nedeniyle bloke etmez ve yazılmaz), yabancı uid’li stage, `nlink>1` stage; hiçbirinde mevcut içerik ezilmez, kimliği kanıtlanmamış dosya silinmez ve yanlış başarı yoktur.
2. İki süreç aynı hedefe: ikincisi `flock` nedeniyle `download_write_failed` alır; yayın bozulmaz.
3. Stage/sidecar durumları: boş stage + sidecar yok (yeniden kullanım), dolu stage + sidecar yok (`download_partial_unverified`), sidecar var + stage yok (sidecar atılır), kalıntı sidecar tmp (sahiplik ✓ silinir / ✗ `download_partial_unverified`), bozuk sidecar, sahiplik ✗, kesin EEXIST sonrası stage/sidecar temizliği; tablo satırlarının hepsi.
4. ENOSPC/kısa yazma/uzun yazma enjeksiyonu: yayın yok, sidecar tutarlı, resume için koşullar doğru; yanlış boyutta yayın yok.
5. Gerçek SIGKILL her yayın adımında (stage açma, sidecar yazma, veri yazma, checkpoint, link öncesi/sonrası, unlink, dizin sync) sonrası durum kapalı beklentilerle doğrulanır; hedef ya yok ya tam ve doğru kimlikte.
6. Sidecar yalnız fsync edilmiş bayt sayısını iddia eder; `prefix_sha256` yerel bozulmayı yakalar; kısa/uzun stage, kimlik farkı ve bozuk sidecar resume’u reddeder; yarım içerik asla sessizce birleşmez.
7. SHA-256 bağımsız hashlib oracle’ıyla eşleşir; sınırı aşan yazma durdurulur; ≤1 MiB blok ve bloklar arası iptal/deadline kontrolü; Unicode ve uzun ad güvenli; checkpoint `os.fsync` ve yayın `full_sync` sürelerinin kaydı P02-3o kanıtı içindir.
8. Manifest yayıncısının mevcut testleri değiştirilmeden geçer.

## Doğrulama

Gerçek dosya sistemi, fork/SIGKILL ve race integration testleri, Ruff, strict mypy. Büyük dosya bellek/süre ölçümü P02-3o’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
