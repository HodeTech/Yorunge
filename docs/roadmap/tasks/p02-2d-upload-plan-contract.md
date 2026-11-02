---
id: P02-2d
phase: P02
status: in_progress
size: M
depends_on: [P02-1]
capabilities: [C03, C12, C13]
---
# P02-2d — Upload planı ve onay sözleşmesi

**Tarih:** 2026-11-02. P02-2 üst paketindeki bağımsız yerel temel; [plan](../p02-2-delivery-plan.md) adım 1. Mevcut a/b/c ID'leri ve remote/live kabulleri korunur.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı özel upload niyetinin yanlış hedefe, yanlış içeriğe veya tekrar gönderime dönüşmesini önleyen gerçek yerel temeli alır. Mevcut generic execution bu transfer sözleşmesini uygulamaz. Bu kartın verified olması uzak upload desteği değildir.

## Giren ve girmeyen kapsam

Strict ayrı plan/manifest bağı, root/hedef/owner/proje, bütçe ve tazelik, digest/onay doğruluğu. Bu kart public dispatch veya uzak producer açmaz. Hesap şartı, credential yaratma, ücretli çağrı, silme, ZIP/import veya ileri resume yoktur.

## Bağımlılıklar ve kararlar

ADR-0024/0025 kullanıcı review düzeltmeleri sonrası Accepted. P02-1 PR #13/50d68b1 ile development'tadır. Kart metadata bağımlılıkları gerçek kabulüne göre doğrulanır; aynı daldaki verified önceki kart yeterlidir. Dış wire/otorite/fiyat kapıları bu yerel temel için gereksiz önkoşul yapılmaz, gerçek producer ve live kabulde korunur.

## Sözleşme ve uygulama sınırı

Kanonik [transfer referansı](../../reference/dataset-transfer.md); domain/application/adapter sınırları korunur. Public caller proof/verified flag veya raw HTTP/SQLite nesnesi enjekte edemez. Eski Plan/Recipe/Execution/jobs/Result biçimleri korunur. Yerel temel ürün CLI'sına sahte pozitif prepared/run desteği eklemez.

## Kabul

Tam canonical wire, bağımsız literal digest/byte oracle, extra/duplicate/bool/float/UTF-8/boyut/sürüm retleri; 128 dosya/500.000.000 byte dosya ve 1 GiB toplam sınırı; plan/grant/cost/approval zaman ve scope eşitliği; kayıpsız aynı-hash farklı adlar. Hata ve kaynak kapanışı gerçek sınırda doğrulanır; anlamlı pozitif/negatif oracıllar uygulama hesaplarından bağımsızdır. Her kod adımı commit ve iki farklı fresh review turuyla kapanır; doğrulanmış bulgular fix/test/commit edilir.

## Doğrulama

İlgili contract/integration/FS/SQLite/TLS kapsamı, Ruff format/lint, strict mypy, belge/skill ve diff denetimi; eski tüketici regresyonları. Son tüm-source kurulum/native/CI kabulü P02-2c'dedir; arada kaynak bağlı eski referans yeni kaynağa başarı diye gösterilmez. Canlı hesap çağrısı bu kartın testi değildir.

## Teslim kaydı

Henüz bu kartın uygulama/test/review kabulü tamamlanmadı. Gerçek commit, iki fresh tur ve kalan sınır oluşunca kayıt eklenecek; remote/live başarı iddiası yoktur.
