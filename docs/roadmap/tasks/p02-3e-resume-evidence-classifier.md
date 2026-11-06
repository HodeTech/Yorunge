---
id: P02-3e
phase: P02
status: draft
size: M
depends_on: [P02-3d]
capabilities: [C03, C12]
---
# P02-3e — Resume kanıt sınıflandırıcısı ve uzak envanter indirgeyicisi

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 2. [ADR-0031](../../decisions/0031-upload-continuation.md) kanıt sınıfları ve soy zinciri; yerel kalıcılık, plan ve yazma yok.

## Kullanıcı sonucu ve mevcut eksik

Kesintiden sonra kullanıcı, hangi dosyanın gerçekten uzakta olduğunu, hangisinin gönderilmesinin güvenli olduğunu ve hangisinin kanıtsız belirsiz kaldığını söyleyecek tek, deterministik bir sınıflandırmaya sahip değildir. Mevcut salt okuma yolu envanteri toplam eşleşmezse hata verir ve dosya bazlı present/missing/conflict kümesi döndürmez; kaynak zincirinin birleşik journal özeti de yoktur.

## Giren ve girmeyen kapsam

Kaynağın soyunun (kök → kaynak; kaynak zincirin ucudur) bütün journal’larının dosya başına birleşik özetini (herhangi bir operation’da accepted confirm makbuzu var mı; yoksa confirm intent’i var mı; zincirde `rejected` makbuz var mı — makbuz içeriği dışarı çıkmaz) ve tam, sayfalı, kapalı sınırlı uzak envanteri alıp kapalı sınıflara (`confirmed`, `observed`, `pending_clean`, `pending_uncertain`, `drift_missing`, `conflict`, `inventory_unreliable`) ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) içindeki kapalı `blockers` kümesine indirgeyen saf mantık, canonical `classification_digest`/`inventory_digest` girer. Mevcut items okuyucusunun yanında non-raising bir indirgeyici ve repository’de salt okuma zincir özeti girer. Kaynak grafiğinin zaten tam olup olmadığının (reconcile önerisi) ve kaynağın zincirin ucu olup olmadığının (`source_superseded`: intent’li torun var) hesabı da girer. Plan/onay tipi, kalıcı yazı, HTTP bileşimi, CLI/API ve continuation yürütmesi girmez.

## Bağımlılıklar ve kararlar

P02-3d belirtimine bağlıdır. [ADR-0031](../../decisions/0031-upload-continuation.md)’in Accepted olması gerekir (bugün Proposed); sınıf tablosu ve güvenlik gerekçesi onaylanmadan başlamaz. Envanter üst sınırı sabittir: 1.024 item; aşan envanter `inventory_unreliable` sınıfı ve `inventory_too_large` engeli olur ve veri sessizce kesilmez.

## Sözleşme ve uygulama sınırı

Sınıflandırma, [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) içindeki kapalı karar tablosunun birebir uygulamasıdır. Giriş: manifest sırası, dosya başına birleşik zincir durumu, uzak item kümesi (ad, boyut, nullable sha256, tekil kimlik). Çıkış: dosya→sınıf vektörü, sayaçlar, plan düzeyi engeller, iki canonical özet. Öncelik: ad çakışması/kopya → `conflict`; yokluk → `drift_missing`; doğrulanamayan envanter → `inventory_unreliable`. Özetler item kimliği ve sağlayıcı zamanını içermez. Kaynak zincir tutarlılığı (döngü, farklı dataset kimliği, kopuk soy) `state_invalid`dir.

## Kabul

1. Tablonun bütün (zincir journal’ı × uzak envanter) hücreleri ayrı beklenen sonuçla sınanır; sınıf, sayaç ve özetler bağımsız elle hesaplanmış vektörlerle eşleşir (üreticinin kendi çıktısı tek oracle değildir).
2. Kaynak journal şekilleri matrisi: yalnız presign; presign+PUT accepted; iki-worker PUT’ta biri unknown; confirm intent var/makbuz yok; accepted confirm. Hepsi doğru birleşik satıra (intent yok / intent var-makbuz yok / accepted) indirgenir; indirgeme varsayılmaz, test edilir.
3. Zincir hücreleri: kök+bir veya iki continuation; confirm intent yalnız kökte; accepted makbuz bir atada; aynı dosya birden çok operation’da denenmiş; sıfır-intent’li bir v3 operation (yalnız `cancelled` torun olarak bulunabilir) birleşime bir şey katmaz ve kaynak olamaz; kaynağın intent’li torunu varsa `source_superseded` (kaynak değil o torun kullanılır); zincirde herhangi bir `rejected` makbuz (savunmacı engel); kaynak grafiği tam (kök 2+3N / v3 3M) iken `reconcile_available`.
4. Saldırgan envanterler: kopya kimlik, aynı ad farklı boyut/SHA, aynı SHA başka ad, fazladan item, null sha256, `total` uyuşmazlığı, cursor döngüsü, 1.024 aşımı; hiçbiri `confirmed`/`observed`/`pending_clean` üretmez ve veri kesilmez.
5. Sıralama ve özet deterministiktir; item kimliği/sıra/zaman değişimi özeti değiştirmez, ad/boyut/SHA değişimi değiştirir.
6. Zincir özeti makbuz içeriğini, anahtarı, URL’yi veya `created_dataset` alanlarını dışarı vermez; salt okuma hiçbir yazı/lease/permit üretmez.

## Doğrulama

Unit/contract/integration (gerçek SQLite journal fixture’ları + loopback TLS items sunucusu), Ruff ve strict mypy. HTTP bileşimi sonraki dilimlerdedir; burada ağ bütçesi iddiası yoktur.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
