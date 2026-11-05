---
id: P02-2f
phase: P02
status: verified
size: M
depends_on: [P02-2d]
capabilities: [C03, C12, C13]
---
# P02-2f — İzole hedef ve streaming storage temeli

**Tarih:** 2026-11-02. P02-2 üst paketindeki bağımsız yerel temel; [plan](../p02-2-delivery-plan.md) adım 4 temel. Mevcut a/b/c ID'leri ve remote/live kabulleri korunur.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı özel upload niyetinin yanlış hedefe, yanlış içeriğe veya tekrar gönderime dönüşmesini önleyen gerçek yerel temeli alır. Mevcut generic execution bu transfer sözleşmesini uygulamaz. Bu kartın verified olması uzak upload desteği değildir.

## Giren ve girmeyen kapsam

Tek owned session/client/toplam iki bağlantıda ayrı StorageRequest portu, public-IP DNS pin/peer guard, descriptor streaming ve kapalı auth/encoding/byte/cancel. Gerçek presign/confirm codec veya canlı transfer bu kart değildir. Hesap şartı, credential yaratma, ücretli çağrı, silme, ZIP/import veya ileri resume yoktur.

## Bağımlılıklar ve kararlar

ADR-0024/0025 kullanıcı review düzeltmeleri sonrası Accepted. P02-1 PR #13/50d68b1 ile development'tadır. Kart metadata bağımlılıkları gerçek kabulüne göre doğrulanır; aynı daldaki verified önceki kart yeterlidir. Dış wire/otorite/fiyat kapıları bu yerel temel için gereksiz önkoşul yapılmaz, gerçek producer ve live kabulde korunur.

## Sözleşme ve uygulama sınırı

Kanonik [transfer referansı](../../reference/dataset-transfer.md); domain/application/adapter sınırları korunur. Public caller proof/verified flag veya raw HTTP/SQLite nesnesi enjekte edemez. Eski Plan/Recipe/Execution/jobs/Result biçimleri korunur. Yerel temel ürün CLI'sına sahte pozitif prepared/run desteği eklemez.

## Kabul

Gerçek iki-origin TLS, DNS mixed/rebind/peer mismatch, exact path/query/header, auth/cookie/log sırrı, expiry/no replay, slow read/cancel/queue/Content-Length/hash; bilinen secret ile dinamik yerel alan ve body sınırları. Native bütünleşik ölçüm P02-2c sahibidir. Hata ve kaynak kapanışı gerçek sınırda doğrulanır; anlamlı pozitif/negatif oracıllar uygulama hesaplarından bağımsızdır. Her kod adımı commit ve iki farklı fresh review turuyla kapanır; doğrulanmış bulgular fix/test/commit edilir.

## Doğrulama

İlgili contract/integration/FS/SQLite/TLS kapsamı, Ruff format/lint, strict mypy, belge/skill ve diff denetimi; eski tüketici regresyonları. Son tüm-source kurulum/native/CI kabulü P02-2c'dedir; arada kaynak bağlı eski referans yeni kaynağa başarı diye gösterilmez. Canlı hesap çağrısı bu kartın testi değildir.

## Teslim kaydı

- PR/commit: [31a6ec3](https://github.com/HodeTech/Yorunge/commit/31a6ec3), [6c5e360](https://github.com/HodeTech/Yorunge/commit/6c5e360), [8eb1809](https://github.com/HodeTech/Yorunge/commit/8eb1809); ayrı PR açılmadı.
- Sonuç: Çalışma dalında verified. 4.1 hedef/source dilimi 6ecb4aa, R1 fix f10292c ve 10f87e1 kapanışıyla; 4.2 network/shared-client dilimi yukarıdaki commitlerle iki farklı fresh review turundan geçti. Son storage/network/source/policy **197 passed / 19,35 s**; iki bulgu/teyit kaydı [uygulama raporundadır](../../research/p02-2-implementation-validation.md#adım-42-fresh-r2). R1 ve R2'deki iki ayrı P2 düzeltildi; hiçbir açık doğrulanmış bulgu kalmadı.
- Kalan sınır: Bu yerel port development'a merge edilmedi; gerçek provider codec, public CLI/API, bütünleşik native/kurulum/CI ve canlı yazma P02-2a/b/c kapsamındadır. Bu kart uzak yetki veya maliyet kanıtı üretmez.
