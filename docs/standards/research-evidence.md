# Araştırma kanıtı ve review kapsamı

**Durum:** Etkin — 2026-10-29 kullanıcı yetkisiyle PR #10 kanıt düzenlemesi. Ürün wire'ı, migration kimliği veya performans bütçesi değişmez.

## Dört ayrı girdi

Araştırma raporları ve kabul iddiaları `docs/research/*.md` altında normal incelemeye girer. Ölçüm betikleri çalıştırılan koddur; hata/güvenlik/yöntem açısından incelenir. Testlerin bağımsız beklentisi olarak okuduğu sabit JSON vektörleri kaynak kodu gibi sürümlenir ve incelenir; üretilmiş ölçüm arşivi sayılmaz.

Büyük üretilmiş ölçümler `docs/research/raw/<name>.json.gz` altında kayıpsız tutulur. [Manifest](../research/evidence-manifest.json) arşiv ve özgün JSON SHA-256/boyutunu, kaynak bilgisini ve bütün örneklerden türetilmiş özeti taşır. [İnsan tarafından okunabilen indeks](../research/evidence.md) aynı manifestten üretilir ve normal review kapsamındadır. Başarısız koşular, önceki kaynak başarıları ve diagnostic-only ölçümler silinmez veya güncel kabul diye yeniden etiketlenmez.

Bu ayrım PR #10'un eklediği 33 ham ölçüme uygulandı. Önceki fazların kök dizindeki kayıtları ve sabit vektörler bu bakımda taşınmadı. Özgün JSON baytları yeniden serileştirilmedi; yalnız dış gzip temsilinde zaman damgası sıfırlandı. Önceki Git commit'leri yeniden yazılmaz; eski JSON blob'ları geçmişte kalır. Yeni ölçümler bu arşiv akışını kullanır.

## Kayıt ve doğrulama

Ölçüm aracı çıktısını Git dışında `dist/` altındaki yeni bir dosyaya yazın. Ardından repo kökünden:

```sh
.venv/bin/python scripts/research_evidence.py archive dist/example-budget.json
.venv/bin/python scripts/research_evidence.py verify
```

`archive` yalnız doğrudan repo `dist/` altındaki canonical JSON dosya adlarını alır; başka checkout yolu, alt dizin, `..` veya symlink girdi alınmaz. Girdi dosyasını silmez, aynı adla kayıtlı arşivi ezmez. Eski bir raporu taşımak gerekirse önce `dist/` altına açıkça kopyalanır; bayt eşliği doğrulandıktan sonra eski kopya ayrı kaldırılır. Yeni örnek için yeni ad kullanılır. Gzip, manifest ve indeks birlikte commit edilir. Tek yazarlı yerel hazırlık aracıdır; bu üç dosyayı güncelleme işlemi tek bir transaction değildir. Hata/kesinti sonrasında girdi korunur; eksik/orphan arşiv veya eski indeks `verify` ile reddedilir, başarılı kayıt sayılmaz.

`verify` CI'da gerçek Git checkout'unda çalışır. Arşiv listesi, sınırlı açma, strict UTF-8/JSON, duplicate/nonfinite reddi, iki SHA-256 ve boyut, özet ve indeks eşliği kontrol edilir. Startup/jobs için bütün sıcak örneklerden nearest-rank p95 ve ilan edilen kapı sonucu yeniden hesaplanır; tarihsel v1 yuvarlama hassasiyeti korunur. Eski başarısız koşunun doğru saklanmış olması bu kontrolü geçebilir: arşiv bütünlüğü, performans kabulü değildir.

Bu araç ölçümü tekrar çalıştırmaz, donanım/komut iddiasını bağımsız kanıtlamaz ve tarihsel kaynak hash'lerini güncel checkout'la eşitlemez. Kaynak kimliği ve hangi sonucun hangi kabulü kapattığı reviewer tarafından değerlendirilir. Hash imza değildir; arşiv ve manifest birlikte değiştirilirse yeni içerik normal review gerektirir.

Eski startup v1 örnekleri ve p95'i üç ondalığa yuvarlar; karar ise yuvarlanmadan önce verilmiştir. Eşiğe yarım mikro-saniye kadar yakın kayıtta özgün pass/fail korunur ve özet bu belirsizliği işaretler. v2/jobs için bu tolerans uygulanmaz. Kurulum özeti bütün origin/cache/execution/jobs smoke sonuçlarını, yardım özeti de beklenen root farkını ve gerçek eşlik sonuçlarını ayrı sayar; eksik alan `not_recorded` kalır. Katalog en çok 256 kayıttır; kapasite doluysa yeni yazı başlamadan ret verilir.

Yeni `installation_v2` kaydı kapalı schema 2 biçiminde iki artifact'ı ve origin/basic/NDJSON/HTTP/stream/cache/execution/jobs kontrollerinin tamamını zorunlu tutar; eksik alan eski kayıt gibi `not_recorded` ile kabul edilmez. Modern jobs kaydı typed stdout/process sayısı, p95 ve kaynak/kurulum/fixture bayraklarını denetler. `raw_stream_budget_v1` kapalı schema 1 biçiminde üç sabit boyutun bağımsız byte/SHA beklentisini, native RSS dönüşümü/farkını, chunk/connection/request sınırlarını, ayrı süreçleri ve provenance tutarlılığını yeniden hesaplar. Dürüst başarısız kayıt arşivlenebilir; uyumsuz `passed=true` reddedilir. Tarihsel kayıtlar bu yeni biçimlere dönüştürülmez. Arşiv yolları raporun üretildiği host'ta varmış gibi yerel dosya sisteminden çözülmez; bu kontroller ölçümün gerçekten yapıldığını onaylayan bir imza değildir.

`verify-jobs-reference NAME` arşiv bütünlüğüne ek olarak [sabit jobs referansını](performance.md#kurulu-jobs-ve-raw-stream-ölçümü) zorunlu denetler: başarılı dört 200 ms/30 süreç sonucu ve ilan edilmiş ortam, tam kaynak hash haritası, kurulu ürün Python baytları ve frozen paket kümesi güncel kaynakla eşleşmelidir. Legacy/eksik/başarısız/yabancı ortam veya herhangi bir kod/fixture/lock/workflow değişimi reddedilir. Commit yalnız belge/arşiv nedeniyle değişmişse byte eşliği korunabilir. Bu, CI'da yeni performans ölçümü veya donanım attestasyonu değildir. Referans kaydı olmadan kapı yeşil olmaz; başka host'un başarısız ölçümü de aynen saklanır.

## İnceleme sırası

Önce ürün kodu/testler, ölçüm betikleri, kabul raporu ve manifest özeti incelenir. Varsayılan tam `git diff` çıktısı veya gzip açılımı model bağlamına dökülmez. Örneğin mevcut taban commit'i seçildikten sonra:

```sh
git diff BASE...HEAD -- . ':!docs/research/raw/**'
.venv/bin/python scripts/research_evidence.py verify
.venv/bin/python scripts/research_evidence.py show p01-4-noop-operation-budget.json
```

Son komut yalnız ihtiyaç duyulan raporun doğrulanmış özgün baytlarını stdout'a verir; normal review'de bütün arşivler açılmaz. Kaynak/ölçüm iddiasında şüphe varsa ilgili ham örnekler ve ölçüm betiği ayrıca incelenir. CodeRabbit `reviews.path_filters` yalnız `docs/research/raw/**` yolunu dışlar; diğer ajanlar bu belgeyi/ajan rehberini uygular. `.gitattributes` aynı dosyaları binary/generated işaretler. Tüm araştırma dizini veya tüm JSON dosyaları dışlanmaz; sabit test vektörleri görünür kalır. [CodeRabbit resmî path kapsamı](https://docs.coderabbit.ai/configuration/path-instructions).

## Paket ve saklama

Ham gzip arşivleri Git'te korunur; sdist/wheel'e dahil edilmez. Paket denetimi raw dizinini ve üyelerini ayrıca reddeder. Manifest/indeks, yöntem, rapor ve gerekli test vektörleri sdist geliştirme girdisidir. İndeksteki ilk kayıt bağlantıları değişmez Git commit'lerine gider; arşivin kendi yerel yolu paket içinde varmış gibi linklenmez. Arşiv tam denetimi Git checkout'u gerektirir.

CI log/artifact saklama süresi tek kalıcı kanıt kaynağı olarak kullanılmaz. İleride ayrı arşiv deposuna geçilirse kalıcı erişim, içerik hash'i ve saklama politikası ayrıca korunur; başarısız kayıtlar yalnız PR'ı küçültmek için atılmaz.
