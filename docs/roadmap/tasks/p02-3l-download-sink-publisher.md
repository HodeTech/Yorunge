---
id: P02-3l
phase: P02
status: draft
size: M
depends_on: [P02-3j]
capabilities: [C03]
---
# P02-3l — Akışlı yerel yazıcı, yarım indirme sidecar’ı ve no-clobber yayın

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 9. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md)#3–#4; manifest yayıncısı kalıbının büyük dosya genellemesi.

## Kullanıcı sonucu ve mevcut eksik

Mevcut tek yayıncı 8 MiB’lık bellekteki manifest içindir. Yüzlerce MiB’lık bir indirmeyi bellekte tutmadan, artımlı hash’leyerek, çökmeye dayanıklı ve hedefi ezmeden yayınlayacak yerel bileşen yoktur.

## Giren ve girmeyen kapsam

Parent zincirinin no-follow doğrulanması, `O_EXCL|O_NOFOLLOW` 0600 stage, async görev içinde ≤1 MiB bloklarla yazma, artımlı SHA-256/bayt sayacı/tavan, deadline noktaları, atomik sidecar güncellemesi (stage `fsync`inden sonra), resume doğrulama ilkelleri (kimlik, boyut, ön ek yeniden hash), tamamlanınca fsync–link–unlink–dizin fsync–kimlik kontrolü yayını ve bilinen kimlikle temizlik girer. HTTP, engine ve tüketici girmez.

## Bağımlılıklar ve kararlar

P02-3j tiplerine bağlıdır. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) onayı gerekir. Manifest yayıncısı kalıbı kopyalanmaz: ortak, `manifest_*` kodlarından bağımsız bir yayın ilkesi çıkarılır ve manifest davranışı değişmez.

## Sözleşme ve uygulama sınırı

Yazıcı DatasetTree/30 s bütçeye bağlı değildir; hedef açık verilen yeni bir dosya adıdır, stage adı hedef adının sabit uzunluklu özetinden türer, kalıcı durum yalnız sidecar’dır. Link çağrısı başladıktan sonraki her belirsizlik `download_write_uncertain`dir ve otomatik tekrar yoktur. Stage SIGKILL ve disk hatasında kalabilir; otomatik silinmez. Dosya modu 0600’dür.

## Kabul

1. Hedef yarışları: hedef önceden var (dosya, dizin, kırık symlink), yayın yarışında oluşur, parent değiştirilir/symlink olur, stage adı ikame edilir; hiçbirinde mevcut içerik ezilmez ve yanlış başarı yoktur.
2. ENOSPC/kısa yazma/uzun yazma enjeksiyonu: yayın yok, sidecar tutarlı, resume için koşullar doğru; yanlış boyutta yayın yok.
3. Gerçek SIGKILL her yayın adımında (stage açma, yazma, sidecar replace, link öncesi/sonrası, unlink, dizin sync) sonrası durum kapalı beklentilerle doğrulanır; hedef ya yok ya tam ve doğru kimlikte.
4. Sidecar çökme tutarlılığı: sidecar yalnız fsync edilmiş bayt sayısını iddia eder; kısa/uzun stage, kimlik farkı ve bozuk sidecar resume’u reddeder ve yarım içerik asla sessizce birleşmez.
5. SHA-256 bağımsız hashlib oracle’ıyla eşleşir; sınırı aşan yazma durdurulur; ≤1 MiB blok ve bloklar arası iptal/deadline kontrolü; Unicode ve uzun ad güvenli.
6. Manifest yayıncısının mevcut testleri değiştirilmeden geçer.

## Doğrulama

Gerçek dosya sistemi, fork/SIGKILL ve race integration testleri, Ruff, strict mypy. Büyük dosya bellek/süre ölçümü P02-3o’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
