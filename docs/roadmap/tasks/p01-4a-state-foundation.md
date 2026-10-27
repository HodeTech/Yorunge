---
id: P01-4a
phase: P01
status: verified
size: M
depends_on: [P01-2a]
capabilities: [C01, C12]
---
# P01-4a — Yerel store ve migration temeli

**Tarih:** 2026-10-27. **Teslim paketi:** [P01-2](../p01-2-delivery-plan.md). Uygulama ve iki yeni bağımsız review turu tamamlandı.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı komutlar ve süreçler arasında aynı kimlik bağını güvenilir biçimde kullanabilmelidir. Kart açıldığında SQLite store, şema sürümü ve migration yoktu; temel teslim edildi.

## Giren ve girmeyen kapsam

Gerçek yerel SQLite açma/kapatma, özel dosya/dizin, şema sahipliği/sürüm, işlemsel migration ve P01-2b'nin tüketeceği kayıt temeli girer. Gelecek operation/attempt/lease/jobs tabloları veya boş API iskeleti kurulmaz. Ağ, EVREN ve tool çalıştırma yoktur.

## Bağımlılıklar ve kararlar

P01-2a aynı dalda gerçek teslim kanıtıyla tamamlanır. [B02/B13 raporuna](../../research/p01-2-state-identity-decision-review.md) bağlı [ADR-0011](../../decisions/0011-state-foundation-and-migrations.md) ve [ADR-0012](../../decisions/0012-credential-identity-and-change-detection.md), 2026-10-27 kullanıcı onayıyla Accepted'dır; şema/yerel koruma bu kararlara uyar. SQLite motoru ADR-0004 ile zaten seçilmiştir. Karar onayı, eksik doğrudan bağımlılığın teslim kanıtı yerine geçmez.

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

- PR/commit: [İlk uygulama](https://github.com/HodeTech/Yorunge/commit/0b668ed), [review 1 düzeltmesi](https://github.com/HodeTech/Yorunge/commit/494799b), [review 2 düzeltmesi](https://github.com/HodeTech/Yorunge/commit/93c4de4); [PR #6](https://github.com/HodeTech/Yorunge/pull/6) kullanıcı review'sine açık.
- Sonuç: 100 state/566 toplam test, Ruff format/lint, strict mypy, belge/ajan; wheel/sdist iki temiz kurulum ve başlangıç bütçeleri geçti. Üçer yeni ajanla iki review turu tamamlandı; dört ilk tur ve bir ikinci tur bulgusu doğrulanıp giderildi, odak kapanışında yeni bulgu yok. [Gerçek kabul kaydı](../../research/p01-2-implementation-validation.md).
- Kalan sınır: Bu alt kartta açık doğrulanmış bulgu/kabul işi yok. Credential gözlemi/reset/restore P01-2b; operation/lease/jobs sonraki P01-4 alt işleridir. Bu adımın ilk kanıtı macOS koşusudur; bütün P01-2 Linux/CPython 3.11.15 CI'ında 757 test ve iki temiz kurulumla ayrıca doğrulandı.
