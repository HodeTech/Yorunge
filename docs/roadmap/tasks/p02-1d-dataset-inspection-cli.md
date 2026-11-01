---
id: P02-1d
phase: P02
status: in_progress
size: M
depends_on: [P02-1a, P02-1c]
capabilities: [C03, C04, C13]
---
# P02-1d — Atomik yerel manifest ve CLI/Python yolculuğu

**Güncellendi:** 2026-11-02. [Paket/adım 4 ve final kabul](../p02-1-delivery-plan.md). Bu kartın tamamı bütünleşik kabulü de gerektirir; arayüzü yazmak verified değildir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı tek yerel komutla manifestini güvenli hedefe kaydeder, sonraki komutla aynı byte kümesini doğrular ve değişimde doğru hata/sonraki adımı alır. Public datasets inspect/verify ve no-clobber manifest artifact’ı çalışma dalında uygulandı; iki fresh kod review turu, üç temiz kurulum turu ve kaynak bağlı native kabulü tamamlandı. Kartın nihai PR/CI ve Linux saklama kabulü açık kalır.

## Giren ve girmeyen kapsam

Descriptor parent’ta 0600 stage/no-clobber publish/sync/cleanup ve belirsizlik; aynı application üstünde public Python API ve datasets CLI, text/JSON/NDJSON, örnek/README/reference/modül/matris/current. Kurulu dağıtım smokes, dosya benchmark’ı, güncel startup/jobs/raw referansları ve son CI/kanıt bu kartın nihai kabulüdür. EVREN, upload/download, execution, veri semantiği, etiket ve archive desteği eklenmez.

## Bağımlılıklar ve kararlar

P02-1a kapasite ve P02-1c scan/verify aynı dalda commit/test/iki fresh turla tamam olmalıdır. ADR-0023 Accepted olmadan ürün kodu başlamaz. [ADR-0018](../../decisions/0018-stream-results-and-cancellation.md) Result/NDJSON ve [ADR-0019](../../decisions/0019-reference-startup-performance.md) kaynak/performance/saklama kuralları korunur. Master/release ve nihai PR merge’ü kullanıcıdadır.

## Sözleşme ve uygulama sınırı

[Manifest referansı](../../reference/dataset-manifest.md) tam API/CLI/DTO/kanonik artifact/hata sınırıdır. Genel hata/exit kataloğu uygulamayla birlikte CLI referansından bu bölüme bağlanır; ikinci bağımsız tablo tutulmaz. Inspect tam listeli artifact ve küçük Result üretir; verify mismatch controlled error/7’dir. Tüm yeni yollar lazy olmalı, help/context eski ucuz yolları bozmaz.

## Kabul

1. Repo dışı temiz wheel ve sdist kurulumunda README’nin sentetik inspect→verify→aynı boyutta değiştir→mismatch yolculuğu gerçek API/CLI ile çalışır. Non-TTY prompt yok, dosya konumu/digest/sayı/sonraki adım metinde bulunur; JSON/NDJSON UTF-8 saf ve aynı typed sonucu verir. Mevcut payload 1 MiB / event 1 MiB + 1 KiB sınırları aşılmaz; özet ≤16 KiB. Kontrol/bidi karakterli root/artifact anchor ve leaf, ayrıca escaping sonrası büyük özet fixture’ı yayın başlamadan reddedilir; tam encoded Result/NDJSON result payload preflight edilir.
2. Hedef source root dışında/parent mevcut koşulu descriptor kimliğiyle denetlenir. Existing regular/directory/symlink/dangling hedef, parent symlink/swap, yarışta hedef oluşturma, kısa write/ENOSPC/fsync/link/unlink hataları eski dosyayı korur ve doğru publication-before/after hatası üretir. 0600 ve aynı parent stage’i gerçek filesystem’de sınanır; overwrite fallback yoktur.
3. Kritik publication çağrısı başlamadan iptal cleanup/no target; link çağrısı başlayıp sonucu kesinleşmeden veya publication sonrası final kontroller bitmeden hata/deadline/iptal KeyboardInterrupt için manifest_write_uncertain/5’tir; gerçek CancelledError cleanup sonrası sabit uncertainty note’u ile aynen yayılır. Gerçek link hedefi oluşturduktan hemen sonra iptal enjekte edilir; EEXIST/2 ayrı kalır. Dayanıklı API başarısından sonraki BrokenPipe/I/O/SIGINT mevcut 6/1/6 kodlarını ve tamamlanmış artifact’ı korur. SIGKILL öncesi stage veya sonrası tam target kalması normal kayıtla ayrılır; startup otomatik silmez. Restart sonrası bağımsız verify tam hedefi kabul eder veya bozukluğu açık reddeder; güç kesintisi kabulü iddia edilmez.
4. Yeni kapalı ErrorCode/mesaj/exit ve ManifestMismatch details testleri; file read ile output write ayrımı, stdout BrokenPipe/locale/SIGINT, CLI tekrar/unsupported option ve platform I/O öncesi ret. Text/JSON/NDJSON input hata mesajları plan hazırlamayan dataset kullanıcısına uygun sonraki adımı söyler. Path/raw exception/içerik traceback’e sızmaz; bilinçli artifact adlarının secret sınıflandırması yapıldığı iddia edilmez.
5. Bağımsız digest byte oracle, parser/scanner/path/atomic negatifleri, tam offline takım, format/lint/strict mypy, belge/ajan ve paket izin listesi/iki temiz kurulum geçer. Yeni smoke ve ölçüm dosyaları paket/review kapsamına doğru girer; raw gzip sdist/wheel’e girmez.
6. Yerel ilk görev fixture’ında inspect→verify sonucu ≤10 s, yardım müdahalesi 0, yanlış/hedef ezme 0; gerçek operatör/ortam/komut kaydedilir. Bu sınırlı sentetik operatör kabulüdür, genel kullanıcı araştırması diye sunulmaz. Performans veri fixture’ları ayrı 30 s/64 MiB/8 MiB hedeflerine [plana](../p02-1-delivery-plan.md#son-kabul-ve-kanıt-sırası) göre geçer.
7. Son kaynakla fresh M5 startup/jobs ve gerçek raw kabulü seri alınır, bütün başarısız/başarılı ham örnekler kalıcı arşivlenir. Üç ortam son PR source CI, aggregate/branch-policy ve Linux tanısı incelenir; hash bağlı raw/receipt/witness takibi kapanır. Mevcut kaynak referansını yeni başarı saymak veya eşiği sessizce büyütmek yoktur.

## Doğrulama

Adım 4 commit ve iki fresh review; ardından final kabul/adım 5 commit ve iki fresh bütünleşik review. Test/build ile benchmark eşzamanlı koşmaz. Çalıştırılmayan/başarısız/atlanan kontroller [kayıtta](../../research/p02-1-implementation-validation.md) açıkça tutulur; saf belge kontrolü ürün kabulü sayılmaz. Gerçek Windows/EVREN çağrısı gerekmez; bunlar iddia edilmez.

## Teslim kaydı

ADR-0023 onaylı, P02-1a/b/c verified; atomik yayın/API/CLI, ölçüm araçları ve iki fresh kod review turu tamamlandı. Üç temiz wheel/sdist kurulum turu, ilk görev ve kaynak bağlı startup/jobs/dataset/raw kabulü geçti. Tam takım 2729ea3’te 4.202 passed/1 Linux-native skip; sonraki CLI düzeltmesi 425 ilgili testle doğrulandı. İki bağımsız gerçek kanıt incelemesinde yeni bulgu yok. Son development PR/CI ve Linux saklama koşulları açık olduğundan bu kart in_progress’tir. Madde bazlı [kabul eşlemesi](../../research/p02-1-implementation-validation.md#p02-1d-kabul-eşlemesi-ve-ölçümden-bağımsız-kapanış) kanoniktir.
