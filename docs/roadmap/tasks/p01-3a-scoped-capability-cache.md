---
id: P01-3a
phase: P01
status: verified
size: M
depends_on: [P01-2b, P01-4a]
capabilities: [C02, C13]
---
# P01-3a — Kapsamlı capability cache ve tazelik

**Tarih:** 2026-10-27. **Paket:** [P01-3](../p01-3-delivery-plan.md). Doğrudan önkoşullar verified; ADR-0013/0014 ve bağlı ScopeV2 2026-10-27 kullanıcı onayıyla Accepted. Adım 1 uygulaması ve iki bağımsız review turu tamamlandı.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı kaydın hangi hedef/hesap/proje/credential/model/araç/ortama ait olduğunu, kanıt düzeyini ve güncelliğini görebilmeli. Mevcut offline görünüm yalnız yerel politika/not-verified verir; kalıcı cache, TTL, clock ve tam scope modeli yoktur.

## Giren ve girmeyen kapsam

Ayrı v2 kayıt, tipli producer/resolver, tam scope anahtarı, gerçek SQLite cache/clock migration, bounded saklama, açık cached/refresh CLI/Python, epoch/nesil kontrolü ve cache tüketicisinin bakım uyumu girer. Eski offline komut/model değişmez. Uzak discovery/HTTP/auth, araç kurma/çalıştırma, execution onayı, operation/lease ve canlı hesap yoktur. Pozitif uzak kanıt yalnız test producer'ıdır; üretimde eksik adaptör unknown/uyumsuzluk olarak kalır.

## Bağımlılıklar ve kararlar

P01-2b/P01-4a [PR #6](https://github.com/HodeTech/Yorunge/pull/6) ile development'ta; [kabul](../../research/p01-2-implementation-validation.md#development-merge-kapanışı). SQLite, HMAC ve binding v1 yeniden seçilmez. [ADR-0013](../../decisions/0013-scoped-capability-cache.md) ile [ADR-0014](../../decisions/0014-execution-plan-validity-and-approval.md) 2026-10-27 kullanıcı onayıyla Accepted; karar kapısı kapandı.

## Sözleşme ve uygulama sınırı

Domain somut SQLite/env/CLI bilmez; application producer/clock/store portlarını koordine eder; gerçek SQLite ve dosya işleri adaptördedir. Public API producer/evidence nesnesi kabul etmez. Kanonik genel referans [capability kaydı](../../reference/capability-record.md), Accepted exact scope [CapabilityScopeV2](../../reference/capability-scope-v2.md), politika ADR-0013'tedir. CLI/Python aynı use case'i çağırır; cached yolun açık state/sır/clock etkisi kullanıcı belgesinde görünürdür.

## Kabul

1. Aynı hesap/projede iki credential, aynı credential'ın farklı API kökü/proje/izin/kaynak/model/sürüm/tool/environment/execution bağları cache paylaşmaz; null wildcard değildir. Kanonik hedef eşitliği binding v1 örnekleriyle tutarlıdır.
2. Belge/sentetik test/yerel credential gözlemi hesap özelinde uzak supported üretmez. Public caller JSON'u/nesnesi cache admission yetkisi değildir; çelişkili kanıt unknown ve görünür nedendir. Bilinmeyen enum/alan/sürüm, duplicate, NaN, aşırı payload kontrollü reddedilir.
3. TTL üst sınırları, tam expiry, future checked_at, ileri/geri saat, restart ve kalıcı clock generation doğrulanır. Watermark'a yetişildikten/restart sonrasında da anomali öncesi cache canlanmaz; ret/rollback bu geçersizleştirmeyi kaybettirmez. Plan/onay tüketicilerinde aynı kapının gerçek kabulü P01-3b'dedir; bu kart tüketicisiz iskeletle onu kanıtlamaz. Stale tarihsel kayıt ile etkin karar ayrıdır; refresh hatası eski supported'ı taze yapmaz.
4. Gerçek DB ve ayrı süreçte A→B→A, gözlem ile cache commit arasına ikinci gözlem, stale writer ve epoch reset sınanır. Eski ID/revision kabul edilmez; env ikinci kez okunmaz ve otomatik retry yoktur.
5. Payload/kanıt/izin ve binding/genel kota sınırları gerçek kayıt hacmiyle doğrulanır. Eski epoch/nesil ve kota temizliği yalnız cache'e dokunur; mevcut identity geçmişi/backup silinmez. Plan/onay eklenince cache temizliğinin onlara dokunmadığı bütünleşik kabulde gerçek tüketicilerle ayrıca doğrulanır.
6. V1 DB'den yeni migration, immutable eski checksum, backup/DDL rollback, iki migration yazarı, busy/IOERR/disk ve bozuk payload kabulü vardır. Full validation eski sürümde yeni tabloyu sorgulamaz; okunan cache satırı ayrıca strict doğrulanır.
7. Cache-only runtime reset/restore/recover açık allowlist'e uyar; eski epoch cache aktif olmaz. Eski restore intent, geçerli stage/live ve kaynak kayıp tamamlanmış çift yeni şemaya güvenli ulaşır; operation runtime yasağı korunur.
8. CLI/API eşit sonuç ve kontrollü hata verir; default offline görünüm ve help/version/env/DB/key guard'ları korunur. Sır/tag/K public JSON, cache payload, hata/repr/loga sızmaz.
9. Standart hacimde 1.024 kayıtla en az 30 ayrı süreçte sıcak cache okuma p95 ≤200 ms; CPU/disk/kurulum/record boyutu kayıtlıdır. Metadata p95 ≤500 ms; kanıt gerçek komut/ölçümle tutulur, başarısız bütçe gevşetilmez.
10. Producer/lock bekleyişinde UTC tam expiry'ye ve ötesine, monotonic toplam bütçeye ilerletilir; son transaction'ın yeni örneği etkin sonucu reddeder. Aynı clock generation ve idempotent cache hit süre kapısını atlayamaz. Commit sonrası gözlenen expiry de taze sonuç vermez; son örnekteki anomali ret/rollback sonrasında restart'ta kalıcıdır.
11. Yeni süreçte authorization scope bilinmiyorsa null exact lookup veya yalnız tarihsel aday/unknown döner; DB kaydı kendi scope'unu doğrulamaz. Bağımsız trusted scope bilinen/değişmiş fixture'da yalnız exact key etkinlik adayıdır. Aday projection en çok dört sonuçla sınırlı, diğer alanların null'ı wildcard değildir ve --cached discovery yapmaz.
12. İki ayrı süreç aynı key için aynı/farklı producer'dan çelişkili refresh üretir: son transaction kanıtları birleştirir, sonuç unknown ve iki provenance korunur. Exact-version snapshot yalnız kendi eski producer kanıtını yeniler; yarışan snapshot kör overwrite yapmaz. Eviction/reinsert token ABA, aynı sonuçta idempotence ve expiry sırasında merge sınanır. Overflow oluşturmayan iki kanıt T+300'e kadar tazeyken T+30 aggregate TTL/temizliği veya TTL öncesi kota baskısı karşı kanıtı kaybettiremez; T+31 tek-producer refresh'i onu silemez. Sekiz kanıt/32 KiB overflow marker'ının TTL/kota/refresh ile erken kaybolmaması ayrıca sınanır.
13. Kapalı ScopeV2'nin eksik/extra/yanlış tür/bool-int/null/UUID/digest/local-remote değişmezleri ve 128 toplam izin-kaynak/16 KiB scope sınırı gerçek parser'da reddedilir. İki bağımsız producer aynı semantik scope için aynı canonical bayt/digest üretir; wire sırasız/duplicate diziyi reddeder, composed/decomposed Unicode birbirine sessiz çevrilmez.

## Doğrulama

Unit kanıt/clock/scope; contract eski v1/new v2/CLI/API/sızıntı; integration gerçek tempfile/SQLite/env, süreç yarışı, migration ve restore kesintisi. [Değişiklik matrisine](../../../CONTRIBUTING.md#doğrulama-seçimi) göre Ruff/mypy/belge/ajan, build/iki temiz kurulum ve ölçüm. Canlı erişim veya yeni dependency kurulumu bu karta dahil değildir.

## Teslim kaydı

- PR/commit: [uygulama a3287b0](https://github.com/HodeTech/Yorunge/commit/a3287b0), [review 1 cd8e812](https://github.com/HodeTech/Yorunge/commit/cd8e812); review 2 saat düzeltmesi ve kapanış aynı dalda kaydedildi.
- Sonuç: [Kanonik uygulama/test/review/performans kanıtı](../../research/p01-3-implementation-validation.md). Son tam takım 929 test; Ruff/strict mypy, belge/ajan denetimi, wheel/sdist iki temiz kurulum ve 1.024 kayıtta cache p95 157,082 ms başarılıdır. İki tur toplam altı yeni reviewer ve son saat bulgusunun bağımsız yeniden probu tamamlandı.
- Kalan sınır: Canlı EVREN/Windows/fiziksel güç kesintisi kanıtı yoktur. P01-3b'nin plan/onay tüketicilerine bağlı bütünleşik kabul kendi adımında sürer; epik henüz tamamlanmadı.
