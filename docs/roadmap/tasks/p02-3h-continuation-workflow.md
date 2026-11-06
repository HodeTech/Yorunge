---
id: P02-3h
phase: P02
status: draft
size: M
depends_on: [P02-3r]
capabilities: [C03, C12]
---
# P02-3h — Continuation üreticisi, alt küme koordinatörü ve proof

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 6. Gerçek TLS/HTTP bileşimi; public CLI/API sonraki dilimdedir.

## Kullanıcı sonucu ve mevcut eksik

Kalıcı v3 kapıları olsa bile sınıflandırmayı taze uzak durumla doğrulayıp yalnız seçili dosyaları güvenle gönderen ve N dosyalık metadata kanıtıyla kapatan bileşim yoktur. Ayrıca mevcut confirm kodlayıcısı `actual_count`’u “bu iş akışında kabul edilmiş confirm sayısı+1” bekler; sağlayıcıda sayı veri seti düzeyinde kümülatif olduğundan dolu bir veri setine devamda ilk confirm yanlış reddedilirdi.

## Giren ve girmeyen kapsam

Pre-admission taze envanter ve yeniden sınıflandırma; kaynak donma çağrısı; mevcut current producer’ın create/link’siz kullanımı (context, detail↔baseline, üyelik, my-role); alt küme koordinatörü (hepsi presign → en çok iki PUT → seri confirm, tek deneme, tek permit); confirm kodlayıcısına taban parametresi (`N−M`) ve v3 oracle’ı (`created=1`, `batch_duplicates=0`, `actual_count == (N−M) + kabul edilen confirm + 1`); `M=0` yalnız doğrulama yolu; N-dosya proof; hata/iptal/belirsizlik eşlemesi; [tüketici referansının](../../reference/platform-upload-consumer.md) `actual_count` tanımının düzeltilmesi girer. Public API/CLI, native ölçüm ve canlı kabul girmez.

## Bağımlılıklar ve kararlar

P02-3e sınıflandırıcısı ve P02-3r yazma kapıları verified olmalıdır. Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §5; yeni replay, politika veya TTL yoktur. v2 kodlayıcısının davranışı (taban 0) değişmez.

## Sözleşme ve uygulama sınırı

Mevcut presign/PUT/confirm codec’leri, bütçe sayaçları ve storage portu v2 yolunda değişmeden kalır; v3 yalnız confirm sayaç tabanını ekler. Taze envanter sınıf özeti kayıtlı plandan farklıysa admission öncesi `upload_plan_not_valid`; PUT sırasında veya proof öncesinde uzak envanter beklenenden sapmışsa mevcut unknown kuralı (yeni etki yok). `created≠1`, kopya, fazladan item ve yanlış toplam başarı değildir.

## Kabul

1. Gerçek loopback TLS sunucusuyla: M>0 başarı (örn. 8 dosyadan 5’i); dolu veri setinde (N−M>0 mevcut item) **her confirm sayaç kontrolünden geçer** (sunucu fixture’ı 4 Kasım kümülatif gözlemini yansıtır); `M=0`; plan–start arası drift; PUT sırasında item ekleme/silme; confirm `created=0`; her aşamada 401/403/429/5xx ve kayıp cevap; her durumda sunucu sayacı create ve project_link isteği **sıfır**, effectful istek sayısı ≤ 3M.
2. Gerçek SIGKILL sınırları (admission, her aşama intent/receipt, iki-worker PUT, proof) v3’te de ikinci etkisiz ve aynı-ID kalır; devam yine bir sonraki continuation veya `reconcile` iledir.
3. Başarılı sonuç yalnız metadata seviyesi ve `remote_bytes_verified=false`; authority/pricing yükseltilmez.
4. Signed URL, ham anahtar, `created_dataset` ve literal credential canary’leri DB/log/exception/çıktıda yoktur; bütçe ve deadline kuralları v2 ile aynıdır.
5. v2 original yolu ve `reconcile` mevcut testlerle değişmeden geçer.

## Doğrulama

Gerçek TLS/süreç/SQLite integration testleri, bütçe sayaç testleri, Ruff ve strict mypy. Kurulu yolculuk ve native ölçüm P02-3i/P02-3a’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
