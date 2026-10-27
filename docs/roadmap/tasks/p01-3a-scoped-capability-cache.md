---
id: P01-3a
phase: P01
status: draft
size: M
depends_on: [P01-2b, P01-4a]
capabilities: [C02, C13]
---
# P01-3a — Kapsamlı capability cache ve tazelik

**Tarih:** 2026-10-27. **Paket:** [P01-3](../p01-3-delivery-plan.md). Doğrudan önkoşullar verified; ADR-0013/0014 onayı eksik olduğu için draft.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı kaydın hangi hedef/hesap/proje/credential/model/araç/ortama ait olduğunu, kanıt düzeyini ve güncelliğini görebilmeli. Mevcut offline görünüm yalnız yerel politika/not-verified verir; kalıcı cache, TTL, clock ve tam scope modeli yoktur.

## Giren ve girmeyen kapsam

Ayrı v2 kayıt, tipli producer/resolver, tam scope anahtarı, gerçek SQLite cache/clock migration, bounded saklama, açık cached/refresh CLI/Python, epoch/nesil kontrolü ve cache tüketicisinin bakım uyumu girer. Eski offline komut/model değişmez. Uzak discovery/HTTP/auth, araç kurma/çalıştırma, execution onayı, operation/lease ve canlı hesap yoktur. Pozitif uzak kanıt yalnız test producer'ıdır; üretimde eksik adaptör unknown/uyumsuzluk olarak kalır.

## Bağımlılıklar ve kararlar

P01-2b/P01-4a [PR #6](https://github.com/HodeTech/Yorunge/pull/6) ile development'ta; [kabul](../../research/p01-2-implementation-validation.md#development-merge-kapanışı). SQLite, HMAC ve binding v1 yeniden seçilmez. [ADR-0013](../../decisions/0013-scoped-capability-cache.md) ile [ADR-0014](../../decisions/0014-execution-plan-validity-and-approval.md) Proposed; açık kullanıcı onayı ürün kodunun kapısıdır.

## Sözleşme ve uygulama sınırı

Domain somut SQLite/env/CLI bilmez; application producer/clock/store portlarını koordine eder; gerçek SQLite ve dosya işleri adaptördedir. Public API producer/evidence nesnesi kabul etmez. Kanonik genel referans [capability kaydı](../../reference/capability-record.md), önerilen ayrıntı ADR-0013'tedir; onay sonrası uygulanan v2 alanları referansta tek yerde belgelenir. CLI/Python aynı use case'i çağırır; cached yolun açık state/sır/clock etkisi kullanıcı belgesinde görünürdür.

## Kabul

1. Aynı hesap/projede iki credential, aynı credential'ın farklı API kökü/proje/izin/kaynak/model/sürüm/tool/environment/execution bağları cache paylaşmaz; null wildcard değildir. Kanonik hedef eşitliği binding v1 örnekleriyle tutarlıdır.
2. Belge/sentetik test/yerel credential gözlemi hesap özelinde uzak supported üretmez. Public caller JSON'u/nesnesi cache admission yetkisi değildir; çelişkili kanıt unknown ve görünür nedendir. Bilinmeyen enum/alan/sürüm, duplicate, NaN, aşırı payload kontrollü reddedilir.
3. TTL üst sınırları, tam expiry, future checked_at, ileri/geri saat, restart ve gözlenen saat anomalisi sonrası eski kanıtın canlanmaması doğrulanır. Stale tarihsel kayıt ile etkin karar ayrıdır; refresh hatası eski supported'ı taze yapmaz.
4. Gerçek DB ve ayrı süreçte A→B→A, gözlem ile cache commit arasına ikinci gözlem, stale writer ve epoch reset sınanır. Eski ID/revision kabul edilmez; env ikinci kez okunmaz ve otomatik retry yoktur.
5. Payload/kanıt/izin ve binding/genel kota sınırları gerçek kayıt hacmiyle doğrulanır. Eski epoch/nesil ve kota temizliği yalnız cache'e dokunur; identity geçmişi/backup ve sonraki plan/onay silinmez.
6. V1 DB'den yeni migration, immutable eski checksum, backup/DDL rollback, iki migration yazarı, busy/IOERR/disk ve bozuk payload kabulü vardır. Full validation eski sürümde yeni tabloyu sorgulamaz; okunan cache satırı ayrıca strict doğrulanır.
7. Cache-only runtime reset/restore/recover açık allowlist'e uyar; eski epoch cache aktif olmaz. Eski restore intent, geçerli stage/live ve kaynak kayıp tamamlanmış çift yeni şemaya güvenli ulaşır; operation runtime yasağı korunur.
8. CLI/API eşit sonuç ve kontrollü hata verir; default offline görünüm ve help/version/env/DB/key guard'ları korunur. Sır/tag/K public JSON, cache payload, hata/repr/loga sızmaz.
9. Standart hacimde 1.024 kayıtla en az 30 ayrı süreçte sıcak cache okuma p95 ≤200 ms; CPU/disk/kurulum/record boyutu kayıtlıdır. Metadata p95 ≤500 ms; kanıt gerçek komut/ölçümle tutulur, başarısız bütçe gevşetilmez.

## Doğrulama

Unit kanıt/clock/scope; contract eski v1/new v2/CLI/API/sızıntı; integration gerçek tempfile/SQLite/env, süreç yarışı, migration ve restore kesintisi. [Değişiklik matrisine](../../../CONTRIBUTING.md#doğrulama-seçimi) göre Ruff/mypy/belge/ajan, build/iki temiz kurulum ve ölçüm. Canlı erişim veya yeni dependency kurulumu bu karta dahil değildir.

## Teslim kaydı

Henüz ürün teslimi yoktur. Kart draft, karar onayı ve uygulama/test/review kanıtı bekler. P01-2'nin geçmiş testleri bu kartın kabulü değildir.
