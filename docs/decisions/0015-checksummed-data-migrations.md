# ADR-0015: Checksum'lı veri dönüşümü için migration manifest v2

**Durum:** Proposed — kullanıcı onayı bekleniyor; uygulanmadı. **Tarih:** 2026-10-28. **İş:** [PR #9](https://github.com/HodeTech/Yorunge/pull/9) P01-3 merge sonrası clock düzeltmesi. [Mevcut manifest kararı](0011-state-foundation-and-migrations.md#şema-ve-migration), [bulgu/kabul kaydı](../research/p01-3-implementation-validation.md#dış-review-kayıtlar-arası-clock-boşluğu-ve-global-fence).

## Bağlam

Accepted ADR-0013, gözlenen ileri saat sonrası süresi bitmiş kayıtların restart/saat geri dönüşüyle canlanmasını engellemeyi ister. PR #9 prototipi bu mevcut garantiyi, bütün cache/proof/conflict ve plan/onay expiry sınırlarını kapsayan türetilmiş indeksle uygular. Bu algoritma yeni TTL, yetki veya dış saat güveni seçimi değildir.

Ancak şema 4→5 mevcut cache kayıtlarından expiry satırları üretmelidir. Python backfill'ini SQL adımlarından sonra çağıran prototip, ADR-0011'deki **“checksum'a girmeyen Python veri dönüşümü bu v1 manifestine eklenmez”** kuralını ihlal eder. V1 checksum yalnız from_version/to_version/statements içerir; dönüşüm kodu değiştiğinde aynı kalır. Bu doğrulanmış P2 giderilmeden prototip merge edilmez.

SQLite alt sınırı 3.37'dir; JSON1 bu sürümde opsiyoneldir. SQL JSON fonksiyonlarını zorunlu kılmak mevcut bağımlılık kararını değiştirir. Sürüm kontrollü, checksum kapsamındaki Python dönüşümü bu ek bağımlılığı gerektirmez. [SQLite JSON1 kaynağı](https://www.sqlite.org/json1.html#compiling_in_json_support).

## Önerilen karar

### V1 kimliklerini koru, veri adımını açık V2 olarak tanımla

1–4 migration'ları aynı SQL baytları ve aynı V1 checksum hesabıyla kalır. V1'e opsiyonel alan eklenerek eski checksum değiştirilmez. SQL-only V1 adımlar çalışmayı sürdürür.

V2 veri dönüşümü gereken yeni adım için açık manifest sürümü taşır. Checksum aşağıdaki kapalı yapının `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")` baytlarının SHA-256'sıdır:

```json
{
  "manifest_version": 2,
  "from_version": 4,
  "to_version": 5,
  "statements": ["<sıralı, değişmez SQL string'leri>"],
  "data_transform": {
    "id": "capability-expiries-v1",
    "code_sha256": "<değişmez handler modülünün 64 hex SHA-256 değeri>"
  }
}
```

Yukarıdaki değerler biçim örneğidir; gerçek SQL/hash uygulamada sabitlenip test edilir. V1+data_transform, bilinmeyen manifest sürümü, bilinmeyen dönüşüm ID'si veya bozuk hash kontrollü reddedilir. `schema_migrations` tablosundaki sürüm/checksum/zaman alanları değişmez; manifest sürümü SQL şema sürümü, backup formatı veya public JSON sürümü değildir.

### Dönüşüm kodunu değişmez ve doğrulanabilir tut

`capability-expiries-v1` yalnız paket içindeki tek, sürümlü handler'a eşlenir. Planlanan handler ayrı ve değişmez bir modüldedir; tam UTF-8/LF kaynak baytlarının hash'i descriptor'daki değerle doğrulanır. Doğrulama hash alanını gerçek handler koduna bağlar; yalnız ad etiketi yeterli değildir.

Handler yalnız standart kütüphane ve kendi değişmez yardımcılarını kullanır. Bugünkü değişebilir domain decoder'ını veya expiry helper'ını çağırarak dönüşüm davranışını checksum dışında bırakamaz. İhtiyacı olan sınırlı JSON/tarih çözümleme ve veri kopyalama mantığı kendi kaynak hash'ine dahildir. Paket içeriğiyle descriptor ayrışması mevcut kontrollü manifest/state hatası olarak reddedilir; ham import hatası/traceback public sonuç olmaz.

ID eşlemesi kodda kapalıdır; tek handler girişi `apply(connection)` olur, davranışı değiştiren caller parametreleri almaz. DB, config, CLI veya caller modül/yol/Python kodu seçemez; genel plugin/exec/SQL-UDF sistemi kurulmaz. Hash bir paket imzası veya aynı UID'de keyfî kod çalıştırmaya karşı güven sınırı değildir; amacı migration'ın hangi değişmez veri algoritmasını kullandığını sabitlemektir.

Hash doğrulaması bekleyen V2 uygulanmadan önce yapılır. Güncel store'un normal açılışında statik descriptor/manifest kimliği doğrulanır; geçmiş dönüşüm modülünü yeniden import/hash etme zorunluluğu eklenmez. Normal CLI/cache başlangıç yolu bu maliyeti taşımaz.

Yayımlanmış handler değiştirilmez. Yeni dönüşüm davranışı yeni handler ID'si ve yeni migration gerektirir. Golden checksum/hash testleri kazara kaynak veya descriptor değişikliğini yakalar. Wheel ve sdist, doğrulanan aynı handler kaynak baytlarını taşır.

### Transaction, doğrulama ve bakım sınırı

Etkilenen adımın handler varlığı/hash'i veri/DDL yazılmadan doğrulanır. Geçerli adımda sıralama SQL DDL → checksum'lı veri dönüşümü → transaction içi manifest kaydı/user_version → tam yapısal/ilişkisel/mantıksal doğrulama → COMMIT olur; hepsi aynı BEGIN IMMEDIATE transaction'ındadır. Doğrulama başarısızsa manifest kaydı ve version dahil adımın tamamı rollback edilir.

Önceki migration snapshot'ı ve dosya/dizin sync kuralları ADR-0011'e göre kalır. Veri/DDL/manifest/version birlikte rollback edilir. Dönüşüm istisnası özgün kontrollü hata sınıfını korur; SQL-UDF sarmalamasıyla I/O hatası veri hatasına dönüştürülmez. Başarısızlık otomatik kullanıcı senaryosu/producer tekrarı başlatmaz.

Şema 5 handler'ı en çok 1.024 cache payload'ını, kayıt başına 32 KiB ve en çok sekiz kanıt sınırlarıyla işler; en çok 10 ayrı expiry/kayıt üretir. Canonical payload'ı, key'i veya proof zamanını değiştirmez. Son tam doğrulama türetilmiş kümenin kaynakla tam eşitliğini denetler. Sıcak okuma/restore/recover doğrulaması ve bilinmeyen operation tüketicisi yasağı korunur.

Varsayılan toplam/busy bütçeleri ve SQLite DELETE/EXTRA/fullfsync politikası değişmez. Uzun zincirde adım başı commit/resume geçerlidir; tüm zincir için tek transaction veya sınırsız bütçe verilmez. Yoğun ve eski restore-stage yükseltmeleri bu handler ile yeniden ölçülür.

### Prototip şema 5'in durumu

Şema 5 development/Master'a merge edilmedi ve yayımlanmadı. PR #9'daki checksum dışı handler yayımlanmış migration sayılmaz; onaydan sonra ilk nihai V2 tanımına değiştirilir. Eski prototip checksum'lı yerel DB otomatik yeniden etiketlenmez, silinmez veya downgrade edilmez; mevcut uyumsuz manifest reddi korunur. Yeni kabul fixture'ları ayrı disposable dizinlerde kurulur; tarihsel ölçüm ve prototip kanıtları korunur.

## Değerlendirilen alternatifler

- **Checksum dışı Python hook'unu korumak:** ADR-0011'e aykırıdır; aynı migration kimliği farklı veri algoritmasını gizler. Reddedildi.
- **JSON1'i zorunlu yapıp SQL backfill kullanmak:** Saf V1 SQL yolunu korur; mevcut SQLite ≥3.37 desteğine ek runtime bağımlılığı getirir. Bu teklif seçmez.
- **Yeni cache'i boşaltmak veya tüm generation'ı sebepsiz artırmak:** Veri/provenance kaybı veya değişmiş kullanıcı davranışı yaratır; indeks türetme ihtiyacı için gerekli değildir.
- **Dönüşümü SQL yorumuna/UDF'ye gizlemek veya migration sonrası görünmez repair yapmak:** Manifest, hata sınıfları ve tamamlanma sınırını belirsizleştirir. Açık, checksum'lı V2 tercih edilir.
- **Sadece handler adı/numarası hash'lemek:** Kodun değişmediğini bağlamaz. Kaynak hash'i ve değişmez handler gerekir.

## Sonuçlar ve kabul kapısı

Bu onay yalnız veri dönüşümlü migration manifestini genişletir. Global expiry garantisini daraltmaz; her volatile UTC örneğinin bire bir kalıcı olduğu şeklinde yeni garanti vermez. Public CLI/Python wire'ı, TTL, cache/plan/onay kotaları, bütçeler, kimlik/K yaşam döngüsü, restore desteği ve gerçek EVREN yetkisi değişmez.

Uygulama kabulünde şunlar gerekir:

- Migration 1–4'ün SQL ve checksum'larının bayt olarak korunması; V2 canonical checksum vektörü.
- Handler kodu/hash/ID/sürüm ayrışmasında kontrollü ret; ilgili adımın DB/manifest/version'ının değişmemesi.
- Backfill ortası, doğrulama ve COMMIT öncesi kesintide rollback; tamamlanmış adımlar üzerinden resume ve iki migration yazarı.
- Şema 2/3/4→5, eski intent/stage/live ve kaynak backup kaybı; payload eşitliği ve index tamlığı.
- Global clock/proof/plan/onay, concurrency, corruption ve churn regresyonlarının korunması.
- Wheel/sdist handler kaynak hash'leri ve iki temiz kurulum; tam test/lint/type/belge, 30-process normal/yoğun başlangıç ölçümleri ve son head zorunlu CI.
- Kullanıcının step başına istediği commit → fresh review 1 → doğrulanmış fix → farklı fresh review 2 döngüsünün tamamlanması.

Onay gelene kadar V2 kodu uygulanmaz; PR #9 taslak kalır. Mevcut V1 dışı backfill, bilinen engelleyici bulgu olarak açık tutulur.
