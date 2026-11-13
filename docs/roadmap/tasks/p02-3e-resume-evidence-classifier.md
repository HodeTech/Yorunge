---
id: P02-3e
phase: P02
status: verified
size: M
depends_on: [P02-3d]
capabilities: [C03, C12]
---
# P02-3e — Resume kanıt sınıflandırıcısı ve uzak envanter indirgeyicisi

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 2. [ADR-0031](../../decisions/0031-upload-continuation.md) kanıt sınıfları ve soy zinciri; yerel kalıcılık, plan ve yazma yok.

## Kullanıcı sonucu ve mevcut eksik

Kesintiden sonra kullanıcı, hangi dosyanın gerçekten uzakta olduğunu, hangisinin gönderilmesinin güvenli olduğunu ve hangisinin kanıtsız belirsiz kaldığını söyleyecek tek, deterministik bir sınıflandırmaya sahip değildir. Mevcut salt okuma yolu envanteri toplam eşleşmezse hata verir ve dosya bazlı present/missing/conflict kümesi döndürmez; kaynak zincirinin birleşik journal özeti de yoktur.

## Giren ve girmeyen kapsam

Kaynağın soyunun (kök → kaynak; kaynak zincirin ucudur) bütün journal’larının dosya başına birleşik özetini (herhangi bir operation’da accepted confirm makbuzu var mı; yoksa confirm intent’i var mı; zincirde `rejected` makbuz var mı — makbuz içeriği dışarı çıkmaz) ve tam, sayfalı, kapalı sınırlı uzak envanteri alıp kapalı sınıflara (`confirmed`, `observed`, `pending_clean`, `pending_uncertain`, `drift_missing`, `conflict`, `inventory_unreliable`) ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) içindeki kapalı `blockers` kümesine indirgeyen saf mantık, canonical `classification_digest`/`inventory_digest` girer. Mevcut items okuyucusunun yanında non-raising bir indirgeyici ve repository’de salt okuma zincir özeti girer. Kaynak grafiğinin zaten tam olup olmadığının (reconcile önerisi) ve kaynağın zincirin ucu olup olmadığının (`source_superseded`: iptal edilmemiş torun var; lease’i dolmamış torun `source_active`) hesabı da girer. Girdi olarak verilen sıralı zincirin tutarlılığı (tekrar eden kimlik/döngü, kök dışında ebeveynsiz kayıt, kopuk soy, farklı dataset kimliği) saf mantıkta doğrulanır; zinciri depodan yürüyen çözümleyici P02-3u’dadır. Plan/onay tipi, kalıcı yazı, HTTP bileşimi, CLI/API ve continuation yürütmesi girmez.

## Bağımlılıklar ve kararlar

P02-3d belirtimine bağlıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir (2026-11-06); sınıf tablosu ve güvenlik gerekçesi onaylıdır. Envanter üst sınırı sabittir: 1.024 item; aşan envanter `inventory_unreliable` sınıfı ve `inventory_too_large` engeli olur ve veri sessizce kesilmez.

## Sözleşme ve uygulama sınırı

Sınıflandırma, [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) içindeki kapalı karar tablosunun birebir uygulamasıdır. Giriş: manifest sırası, dosya başına birleşik zincir durumu, uzak item kümesi (ad, boyut, nullable sha256, tekil kimlik). Çıkış: dosya→sınıf vektörü, sayaçlar, plan düzeyi engeller, iki canonical özet. Öncelik ve güvenilirlik kuralı sözleşmededir: gözlenmiş çelişki her zaman `conflict`tır; envanter güvenilmezse çelişkisi olmayan her dosya `inventory_unreliable` olur ve yokluk/tekillik iddia edilmez. Özetler item kimliği ve sağlayıcı zamanını içermez. Kaynak zincir tutarlılığı (döngü, farklı dataset kimliği, kopuk soy) `state_invalid`dir.

## Kabul

1. Tablonun bütün (zincir journal’ı × uzak envanter) hücreleri ayrı beklenen sonuçla sınanır; sınıf, sayaç ve özetler bağımsız elle hesaplanmış vektörlerle eşleşir (üreticinin kendi çıktısı tek oracle değildir).
2. Kaynak journal şekilleri matrisi: yalnız presign; presign+PUT accepted; iki-worker PUT’ta biri unknown; confirm intent var/makbuz yok; accepted confirm. Hepsi doğru birleşik satıra (intent yok / intent var-makbuz yok / accepted) indirgenir; indirgeme varsayılmaz, test edilir.
3. Zincir hücreleri: kök+bir veya iki continuation; confirm intent yalnız kökte; accepted makbuz bir atada; aynı dosya birden çok operation’da denenmiş; sıfır-intent’li bir v3 operation (yalnız `cancelled` torun olarak bulunabilir) birleşime bir şey katmaz ve kaynak olamaz; kaynağın iptal edilmemiş (intent’li veya başarıyla biten) torunu varsa `source_superseded` (kaynak değil o torun kullanılır; başarıyla bitmişse devam gerekmez); zincirde herhangi bir `rejected` makbuz (savunmacı engel); kaynak grafiği tam (kök 2+3N / v3 3M) iken `reconcile_available`.
4. Saldırgan envanterler: kopya kimlik, aynı ad farklı boyut/SHA, aynı SHA başka ad, fazladan item, null sha256, `total` uyuşmazlığı, cursor döngüsü, 1.024 aşımı; hiçbiri plan hazırlanabilir sonuç vermez, etkilenen dosyalar güvenli sınıfa (`confirmed`, `observed`, `pending_*`) düşmez ve veri kesilmez (envanter kapıları: null hash, kopya kimlik, `total` uyuşmazlığı, cursor döngüsü, 128 sayfa, 1.024 item).
5. Sıralama ve özet deterministiktir; item kimliği/sıra/zaman değişimi özeti değiştirmez, ad/boyut/SHA değişimi değiştirir.
6. Zincir özeti makbuz içeriğini, anahtarı, URL’yi veya `created_dataset` alanlarını dışarı vermez; salt okuma hiçbir yazı/lease/permit üretmez.

**Kabul kapsamı.** Bu adımda kaynak uygunluğu (`source_terminal`, `source_ineligible`, `source_active`, `create_unknown`, `source_superseded`) ve tek önerilen eylem saf işlevlerle (`source_blockers`, `descendant_verdict`, `recommended_action`) sınanır; bunları besleyen tek okuma anlık görüntüsü P02-3u’dadır. Zincir hücreleri (kök+bir/iki continuation, yalnız kökte intent, çok operation’da denenen dosya, sıfır-intent’li operation, torun karar tablosu) saf `merge_chain`/`descendant_verdict` ile sınanır; gerçek SQLite journal’ları bugün yalnız v1/v2 köklerdir. Çok-operation’lı gerçek geçmiş ve zincirin depodan çözülmesi P02-3u’da, “sıfır-intent’li v3 operation kaynak olamaz” hücresi P02-3r/3h’de sınanır.

## Doğrulama

Unit/contract/integration (gerçek SQLite journal fixture’ları + loopback TLS items sunucusu), Ruff ve strict mypy. HTTP bileşimi sonraki dilimlerdedir; burada ağ bütçesi iddiası yoktur.

## Teslim kaydı

- PR/commit: tek development PR’ı ([PR #15](https://github.com/HodeTech/Yorunge/pull/15)) bu daldan açıldı ve 2026-11-12’de [69efc8d](https://github.com/HodeTech/Yorunge/commit/69efc8d465078257257d6494e15fda0e360b01e2) merge commit’iyle development’a alındı; adım commit’leri artık development tarihçesindedir: uygulama [a515a6a](https://github.com/HodeTech/Yorunge/commit/a515a6a6774176d0f8cddb41cb924c22fc4e4621), R1 düzeltmeleri `21b9473` ve `d672eca`, R2 düzeltmeleri [4e06140](https://github.com/HodeTech/Yorunge/commit/4e061405706f561dc7945c20f5661b8c6a54c0c9); kontrol çıktıları ve review kaydı [uygulama kaydındadır](../../research/p02-3-implementation-validation.md#adım-2--p02-3e-resume-kanıt-sınıflandırıcısı-ve-uzak-envanter-indirgeyicisi).
- Sonuç: Kapalı kanıt tablosu (zincir journal birleşimi × uzak envanter → dosya sınıfı), kapalı sıralı plan düzeyi engeller, iki canonical özet, kaynak ve torun uygunluğu ile tek önerilen eylem saf ve bağımsız oracle’larla sınanmış işlevlerdir; journal olguları ve hata vermeyen envanter toplayıcı gerçek SQLite ve gerçek TLS ile doğrulanmıştır (276 yeni test; tam paket 7075 passed, 1 skipped; Ruff, strict mypy, check-docs ve check-agent-guides temiz). R1 ve R2’nin (karar tablosu/oracle, güvenlik/mutasyon, tüketici uyumu, düzeltme doğrulaması/kırılganlık) doğrulanmış bulguları işlendi; yeni testler her tur 31–47 mutantlık özdenetimlerde eşdeğer olmayan hiçbir mutantı hayatta bırakmadı.
- Kalan sınır: *Dilim kapanışındaki durum; tarihsel kayıt olarak korunur. Sonradan: bu kartın ertelediği dilimlerin hepsi teslim edildi; envanter toplayıcıyı P02-3h’nin `resume` raporu çağırır (`upload_resume.py`) ve public yüzey P02-3i ile teslim edildi. Güncel durum [epik kapanışındadır](../../research/p02-3-implementation-validation.md#development-merge-kapanışı).* Dilim kapanışında: Yalnız saf mantık ve salt okuma veri yoludur: plan/onay/kayıt tipleri (P02-3f/3t), zincirin depodan çözülmesi ve kaynak/torun olgularının tek okuma anlık görüntüsü (P02-3u), yazma kapıları (P02-3r), taze envanterin iş akışına bağlanması (P02-3h) ve public yüzey (P02-3i) sonraki dilimlerdedir; envanter toplayıcı henüz hiçbir ürün iş akışından çağrılmaz. Sağlayıcının tutarlı `total` bildirip bir item’ı sessizce atlaması tespit edilemez (kalıcı sınır). Yerel sözdizimini bozan yabancı item listeyi `invalid_response` hatasına çevirir (bilinçli). Canlı davranış iddiası yoktur.

Seçilen adlar ve yerleşim:

- Saf mantık `yorunge.domain.upload_resume`: kapalı sözlükler (`FILE_CLASSES`, `BLOCKERS`, `CHAIN_STATES`); `OperationJournal`/`StageFact` olguları; `merge_chain(journals, manifest)` (aynı manifest üzerinde sıralı soy zinciri; tutarsız veya yabancı zincir `state_invalid`) ve `ChainSummary` (kendini doğrular, manifest özetini taşır); `RemoteInventory`/`InventoryFold` (128 sayfa ve 1.024 item sınırı, cursor döngüsü, `total` tutarlılığı); `classify(manifest, chain, inventory)` ve doğrulanan `Classification` (sınıf vektörü, kapalı sıralı engeller, iki özet; `count`, `indices`, `with_blockers`, `plannable`); engel yokken `selection()` ile `ContinuationSelection` (`file_indices`, `uncertain_indices`, `remote_present_count`); `descendant_verdict`, `SourceFacts` ile `source_blockers` ve `recommended_action`; `ContinuationNotPossible` P02-3f’de eklenir. P02-3t iki ek yaptı (davranış değişmeden): `chain_blockers(ChainSummary)` günlük engellerini (`reconcile_available`, `known_negative`) envantersiz verir ve `classify` onu kullanır; `Classification.manifest_digest` sınıflandırmanın indekslendiği manifestin özetini taşır.
- Journal olguları `yorunge.adapters.upload_chain.operation_journal` ve `StateUploads.operation_journal(operation_id)` (salt okuma; makbuz içeriği, anahtar, URL veya `created_dataset` taşımaz; v1/v2 operation’ları zincir köküdür, başka plan türü `state_invalid`; hata operation kimliğini korur).
- Envanter toplayıcı `read_inventory` / `ObservedUploadPort.inventory` mevcut `read_items`ın yanındadır; manifest ile karşılaştırmaz, içerik tutarsızlığında hata vermez, biçimi bozuk sayfa/başka dataset/yerel sözdizimini bozan item/taşıma hatasında mevcut kodlarla hata verir. `ProviderItemsPage` gevşek sayfa modelidir; `ProviderItems` değişmedi.
- Uygulama sırasında bulunan belirsizlik: referanstaki öncelik cümlesi `drift_missing`i `inventory_unreliable`dan üstün tutuyordu; güvenilmez listede yokluk iddia edilemeyeceğinden öncelik sözleşmede netleştirildi: gözlenmiş çelişki `conflict`, güvenilmez envanter çelişkisiz her dosya için `inventory_unreliable`, güvenilir envanterde tablo.
