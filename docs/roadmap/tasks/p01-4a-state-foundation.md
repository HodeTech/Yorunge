---
id: P01-4a
phase: P01
status: draft
size: M
depends_on: [P01-2a]
capabilities: [C01, C12]
---
# P01-4a — Yerel store ve migration temeli

**Tarih:** 2026-10-27. **Teslim paketi:** [P01-2](../p01-2-delivery-plan.md). B02/B13 onayı ve P01-2a kanıtı beklenir; uygulama yoktur.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı komutlar ve süreçler arasında aynı kimlik bağını güvenilir biçimde kullanabilmelidir. Bugün SQLite store, şema sürümü ve migration yoktur.

## Giren ve girmeyen kapsam

Gerçek yerel SQLite açma/kapatma, özel dosya/dizin, şema sahipliği/sürüm, işlemsel migration ve P01-2b'nin tüketeceği kayıt temeli girer. Gelecek operation/attempt/lease/jobs tabloları veya boş API iskeleti kurulmaz. Ağ, EVREN ve tool çalıştırma yoktur.

## Bağımlılıklar ve kararlar

P01-2a aynı dalda gerçek teslim kanıtıyla tamamlanır. [B02/B13 raporu](../../research/p01-2-state-identity-decision-review.md), [ADR-0011](../../decisions/0011-state-foundation-and-migrations.md) ve [ADR-0012](../../decisions/0012-credential-identity-and-change-detection.md) onaylanmadan şema/yerel koruma kesinleştirilmez. SQLite motoru ADR-0004 ile zaten seçilmiştir.

## Sözleşme ve uygulama sınırı

Domain somut SQLite bilmez; kayıt yaşam döngüsü dış adaptördedir. Model/adaptör adları uygulama kararıdır; bu kart henüz olmayan import arayüzü ilan etmez. Okuma ile yaratma/migration ayrılır. PRAGMA ve desteklenen runtime sürümü varsayılmaz, geri okunur; gelecekteki state tüketicileri aynı transaction otoritesini kullanır.

## Kabul

1. Yardım/sürüm ve mevcut offline kullanım store/dizin/key oluşturmaz. Açık store kullanımı gerçek geçici DB'de kapanıp yeniden açılır.
2. Onaylı PRAGMA, application/schema kimliği, sürüm ve bütünlük denetlenir; yabancı/gelecek/bozuk DB sessizce yenisiyle değiştirilmez.
3. Migration DDL/veri/sürüm kaydı adım başına birlikte commit veya rollback olur; 1→2 başarılı/2→3 başarısız zincir 2'de yeniden açılır. Manifest checksum/süreklilik/sürüm değişmezi, ilişkisel/mantıksal tutarlılık, süreç kesintisi ve iki migration yazarı deneyi kanıtlıdır.
4. Kilit beklemesi sınırlıdır; hata kontrolsüz traceback, sahte başarı veya sessiz veri sıfırlaması üretmez. Transaction içinde ağ/uzun hash beklenmez.
5. Dosya/dizin izinleri, symlink ve yetersiz yazma alanı senaryoları desteklenen macOS/Linux'ta anlamlı negatif testle doğrulanır. NFS/bulut senkronizasyon dizini desteği varsayılmaz.
6. ADR-0011'in no-clobber backup, tamamlanma kaydı, saklama ve platform sync sırası gerçek dosyalarla sınanır; mevcut hedef/disk dolması/üst dizin sync hatasında DDL başlamaz. Kısmi yedek restore girdisi sayılmaz, başarılı snapshot otomatik silinmez. Hot-journal açılış kurtarması ile manuel journal silme ayrımı korunur.

## Doğrulama

Gerçek tempfile/SQLite ve ayrı süreçlerle commit/rollback, migration, kilit ve yeniden açma; kaynak yönetimi ve lazy guard. İlgili testler, format/lint/strict mypy ve paket/import etkisine göre build/temiz kurulum/başlangıç kontrolü [CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi) ile seçilir.

## Teslim kaydı

Henüz ürün uygulaması, test sonucu veya teslim PR'sı yoktur. Bu alt iş P01-2 ile aynı PR'da teslim edilecek; özgün ID'si korunur.
