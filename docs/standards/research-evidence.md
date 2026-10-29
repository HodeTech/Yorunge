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

Güncel bellek kabulü `raw_stream_budget_v2` / schema 2 kapalı kaydıyla yapılır: anlık baseline, pre/post lifetime peak ve native yöntem/birim, ek RSS alt/üst sınırları yeniden hesaplanır. 64 MiB üst sınır ve [performans standardındaki](performance.md#kurulu-jobs-ve-raw-stream-ölçümü) 8 MiB çapraz boyut aralık kapısı producer kararından bağımsız doğrulanır. Dürüst growth-failure arşivlenebilir; bütün tekil koşular yeşilken sahte overall başarı reddedilir. V1 dalı tarihsel bütünlüğü aynı eski özetle korur; v1'in passed=true değeri yeni bellek kabulüne yükseltilmez.

`verify-jobs-reference NAME` arşiv bütünlüğüne ek olarak [sabit jobs referansını](performance.md#kurulu-jobs-ve-raw-stream-ölçümü) zorunlu denetler: başarılı dört 200 ms/30 süreç sonucu ve ilan edilmiş ortam, tam kaynak hash haritası, kurulu ürün Python baytları ve frozen paket kümesi güncel kaynakla eşleşmelidir. Legacy/eksik/başarısız/yabancı ortam veya herhangi bir kod/fixture/lock/workflow değişimi reddedilir. Commit yalnız belge/arşiv nedeniyle değişmişse byte eşliği korunabilir. Bu, CI'da yeni performans ölçümü veya donanım attestasyonu değildir. Referans kaydı olmadan kapı yeşil olmaz; başka host'un başarısız ölçümü de aynen saklanır.

## İnceleme sırası

### Startup evidence v1

[ADR-0019](../decisions/0019-reference-startup-performance.md) Accepted; yeni `startup_evidence_v1` / `schema_version=1` eski startup v2 arşivlerinin yerine geçirilmez. `check-startup-evidence.py` yeni iki wheel/venv ve ayrı 1.024 kayıtlı fixture hazırlar; aynı-host AB/BA ölçümü sıfırdan çalıştırır. Üst düzey kapalı alanlar `schema_version`, `report_kind`, `source_commit`, `measurement`, `snapshots`, `output_checks`, `measurement_exit`, `passed`'dir.

`measurement`, startup v2'nin tam kapalı ham alan kümesini taşır: ortam (`python/platform/machine/cpu/cpu_affinity/runner_image/disk_type`), `cache_dataset`, profil byte/hash'i, `samples_per_command`, `installation/cold_method/cpu_method`, dört `measurements` ve aynı-host `comparison`. Her ölçüm ilk süreç, tam 30+ sıcak örnek, median/p95, üç CPU tanı dizisi, 500/200 ms hedefi, `passed` ve cache-hit bayrağını içerir. `comparison` taban dataset/ölçümlerini, tam eşli oranları ve sabit yöntem/kabul metnini taşır. Sürüm ve sayaçlar gerçek `int`'tir; bool/float sayaç, eksik/fazla anahtar, nonfinite, p95/median/oran/exit uyuşmazlığı reddedilir.

`snapshots.before/after` her iki tarafta `candidate/baseline` içerir. Her tarafın tam alanları `source`, `installed`, `runtime_data_sha256`, `fixture`, `wheel_path`, `wheel_sha256`'dir. Source, commit ve tam public Python/test/script + pyproject/lock/profil ve bütün `.github/workflows/**` dosyalarının haritasıdır; ayrıca `py.typed` bağlanır. Installed, mevcut jobs runtime'ının kapalı Python/SQLite/paket, import/console kökeni ve Python/konsol hash alanlarını kullanır; `runtime_data_sha256` kurulu `py.typed` eşliğini sağlar. Fixture tam alanları `state/profile`, profil hash/byte, `records/payload_bytes/largest_record_bytes`, bütün cache satırlarının ve expiry satırlarının kanonik `cache_sha256/expiries_sha256` özetidir. Mutasyona açık cache clock gözlem metadata'sı fixture içerik özeti değildir. Her iki tam snapshot birebir aynı olmalıdır; kurulu Python/data kaynakla eşleşir, farklı venv/state zorunludur. Her iki taraf aday kaynak girdisine bağlanan aynı profili tüketir; tarihsel taban checkout profilinin yorum baytları farklı olabilir.

`output_checks.candidate/baseline` dört komut için tam `typed_stdout_verified/verified_processes/stdout_sha256/wall_ms/expected_version/expected_python` alanlarını taşır. Her ilk süreç, üç ısınma ve bütün sıcak örnek için bounded strict UTF-8/JSON, kurulu Result tipi ve sabit profile/cache beklentisi süre dışında doğrulanır; help/version da içerik oracle'ından geçer; her taraf kendi kurulu ürün sürümünü ve ayrı `-I` Python sürecinde kendi wire modelini kullanır. Byte hash ve ölçülen wall süresi bütün süreçler için korunur; sıcak dizi ve ilk süreç ham ölçümle eşleşir. Exit 0 tek başına kanıt değildir.

`verify-startup-reference NAME` arşiv bütünlüğünü, dört başarılı mutlak hedefi, ilan edilmiş M5/SSD/Python 3.11 ortamını, güncel **tam** kaynak haritasını ve frozen runtime paketlerini zorunlu denetler. Wheel SHA yalnız tarihsel artifact kimliğidir; yeni checkout wheel arşivinin hash'iyle karşılaştırılmaz. README metadata açıklaması değişebilir; ölçüm içi kurulum/konsol/wheel değişimi veya sonradan runtime/entry point/lock/workflow/test değişimi geçemez. Hash fiziksel donanım attestasyonu değildir. Linux görünürlük/kalıcı arşiv sorumluluğu ve iptal kuralları [karardadır](../decisions/0019-reference-startup-performance.md#linux-tanısının-görünürlüğü-ve-kalıcı-saklanması); CI entegrasyonu tamamlanana kadar bu formatın varlığı yeni kabul sayılmaz.

### Linux startup tanı receipt'i

`startup_ci_diagnostic_v1` / schema 1 tam alanları `schema_version/report_kind/source_commit/run_url/report_name/report_sha256/producer_exit/outcome/reason/p95_ms`'dir. Tamamlanmış geçerli ölçümde `outcome=passed|diagnostic_budget_exceeded`, `reason=validated`, sekiz aday/taban p95 ve özgün raw dosyasının SHA-256'sı zorunludur. `producer_exit` yeniden hesaplanan mutlak aday kararına uyar; 2 saniyelik aşım tanı olarak saklanabilir, performans `passed` olmaz. Error receipt'i `outcome=error`, boş p95 ve kapalı `measurement_failed|invalid_evidence|missing_evidence` nedeni taşır; genel CI kapısını geçemez. Bool sayaç, nonfinite, eksik/fazla anahtar ve sahte outcome reddedilir.

CI upload öncesi guard, tamamlanmış receipt'in ham rapor byte hash'i, tam kaynak/pinned taban, outcome ve p95 ile eşliğini tekrar doğrular. Receipt'in tek başına arşiv bütünlüğünü geçmesi raw ölçüm kabulü değildir. İndirilen özgün raw ve receipt farklı yeni arşiv adlarına kopyalanır, bayt/hash eşliği korunur ve **ikisi** kalıcı Git arşivine alınır; kabul raporu run URL ve hash ilişkisini bağlar. Eksik/iptal koşunun olmayan örnekleri oluşturulmaz; açık saklama takibi kapatılmadan sonraki kabul/merge önerisi verilmez. Artifact upload için `if-no-files-found=error` ve 90 gün retention kullanılır ([resmî action girdileri](https://github.com/actions/upload-artifact/tree/v4#usage)); artifact tek kalıcı kanıt değildir.

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
