---
id: P01-3b
phase: P01
status: verified
size: M
depends_on: [P01-3a]
capabilities: [C02, C12, C13]
---
# P01-3b — Execution hazırlığı, geçerlilik ve onay bağı

**Güncellendi:** 2026-10-28. **Paket:** [P01-3](../p01-3-delivery-plan.md). ADR onayları ve P01-3a kabulü tamamlandı; dört adımın yerel kabulü ve ikişer review tamamlandı; [PR #8](https://github.com/HodeTech/Yorunge/pull/8) 2026-10-28 tarihinde development'a [merge e32cb42](https://github.com/HodeTech/Yorunge/commit/e32cb4289e12a15aeb8c8037c0fca4fc6a7082aa) ile alındı; merge sonrası CI başarılıdır.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı planın hangi girdiler/hedef/yetkiyle hazırlandığını saklayabilmeli; değişmiş bağla eski plan veya onay geçerli sayılmamalı. İşe başlarken offline Plan yalnız şema/seçim doğrulamasıydı; bu kart ayrı execution modeli, güncel bağ doğrulaması, kalıcı plan/onay ve public validity yüzeyini tamamladı.

## Giren ve girmeyen kapsam

Ayrı execution v2 snapshot, yerel dosya bağlama, kalıcı prepare/list/show/validate, güncel doğrulama sonrası açık digest approval/revoke/forget, kota ve yeni tüketicinin reset/restore/recover/preview uyumu girer. Mevcut offline Plan byte/digest ve seçim önceliği korunur. Run/start, operation/attempt/lease/jobs, HTTP, gerçek EVREN ve ForgeLM/muadil adaptörü yoktur. Test fixture pozitif hazırlığı ürün desteği değildir; public görevler adaptör eksikliğini blocked/non-executable gösterir.

## Bağımlılıklar ve kararlar

P01-3a aynı dalda kendi kabulü ve iki bağımsız review turuyla verified; ayrı merge gerekmez. [ADR-0013](../../decisions/0013-scoped-capability-cache.md)/[ADR-0014](../../decisions/0014-execution-plan-validity-and-approval.md) 2026-10-27 kullanıcı onayıyla Accepted; P01-3a önkoşul kanıtı uygulama kaydındadır. Temel bağların nedeni Accepted ADR-0004/0005/0011/0012 ve [execution mimarisidir](../../architecture/execution-model.md).

## Sözleşme ve uygulama sınırı

Domain plan/girdi/onay kuralları; application güncel tipli producer, dosya ve state portlarını koordine eder; CLI parse/render yapar. Public caller doğrulanmış girdi/izin veya onay nesnesi enjekte edemez. V2/CLI/approval/bakım kararları ADR-0014'tedir; uygulanan exact alanlar execution referansında, public komut/hatalar CLI/state referansında tutulur. Yeni şema eski `load_plan` politikasını zayıflatmaz.

## Kabul

1. Eski v1 golden Plan aynı JSON/digest ile üretilir/yüklenir; güncel profil değişimi saved seçimi yeniden çözmez, v1 execution'a otomatik yükselmez. V2 yükleme/yapı bütünlüğü güncel validity veya onay sayılmaz.
2. Gerçek yerel dosya, descriptor/stat ve bloklu hash ile bağlanır. Aynı boyut/mtime değişimi, symlink/kök dışı/absolute/traversal yol, hash sırasında değişim, 30 saniye/1 GiB okuma bütçesi aşımı güvenli reddedilir. 16 MiB/256 MiB/1 GiB fixture'da 1 MiB blokla hash belleği boyutla büyümez; kısmi hash başarı değildir. Manifest dosyasını hash'lemek tüm data closure/model ağırlığını doğrulamış gibi anlatılmaz.
3. Fixture producer ile olumlu preparation ve public üreticide eksik araç/uzak kanıt engelleri ayrı test edilir; hiçbir public sentetik görev/backend veya run eklenmez. State/IO hatasında sahte başarı yoktur.
4. Saved plan değişmeden güncel API kökü/origin/hesap/proje/credential ID/nesil/izin/kaynak/model revision/içerik/tool executable/environment/runtime/parametre farkında validity reddedilir. Aynı secret snapshot kullanılır; son transaction'da epoch/revision tekrar denetlenir; çatışma otomatik retry edilmez.
5. Plan/capability/tahmin expiry'si ve kalıcı clock generation geçerliliği sınırlar. Saat watermark'a yetişince veya restart sonrası eski plan/onay canlanmaz. Yalnız yeni kontrol zamanı, aynı semantik karar için planı değiştirmez veya ilk expiry'yi uzatmaz. Güncel validation sonraki dispatch bileti değildir.
6. Eksik/yanlış digest çıkış 4; blocked/geçersiz plan approval çıkış 2'dir. Doğru açık onay yalnız aynı plan/schema/digest/store/epoch/süre için kayıt olur. Tekrarlı geçerli onay idempotent yerel sonuçtur; revoke sonraki kullanımı reddeder. Non-TTY prompt/sessiz onay yoktur; insan kimliği veya exactly-once garantisi iddia edilmez.
7. Plan/onay kotası ve bounded/sayfalı list gerçek DB'de sınanır. Önceden ID bilgisi olmadan dolu store → list ile plan bul → doğru digest ile forget → yeni prepare akışı tamamlanır. Forget yalnız seçilen planı ve transaction anındaki bağlı onayı atomik siler; başka kayda veya cache/identity/backup'a dokunmaz. Eşzamanlı approval/revoke için bu davranış ayrı süreçte doğrulanır. Planı unutmak uzak iptal değildir; gelecek operation bağı silmeyi engelleyecek açık devir koşuludur.
8. Reset/restore local-only dahil eski cache/plan/onay etkinliğini bitirir. Preview sonrası yalnız plan/onay değişiminde confirmation stale olur; cache-only değişim onayı bozmaz. Bakım preview v2 kayıp/etkisizleşme kapsamını gösterir.
9. Gerçek önceki runtime intent'inde stage yok/eski stage/eski live; tamamlanmış pair'de kaynak backup kayıp; yeni şema/kalıcılık öncesi kesinti senaryoları recover ile güvenli tamamlanır. Bozuk payload epoch değişimiyle aklanmaz; operation-capable runtime'da eski snapshot/intent ile kaçış yoktur.
10. CLI/Python prepare/list/show/validate/approve/revoke/forget aynı kuralları ve kontrollü JSON/hata zarfını kullanır. Secret/tag/K yeni public payload/digest/repr/loga girmez; list/show env/girdi okumaz. Metadata ve mevcut offline guard/performance bütçeleri korunur.
11. Plan/onay gerçek tabloları eklendikten sonra cache expiry/nesil/kota temizliği bu kayıtları veya başka kritik geçmişi silmez; bütünleşik gerçek DB kabulü P01-3a'nın cache-only testlerini tamamlar.
12. Root/ancestor/ara dizin ve son bileşen tam open öncesinde symlink veya FIFO ile değiştirilir; dış sentinel'dan bayt okunmadan kontrollü ret, descriptor kapanışı ve gerekli platform/dir_fd/flag yokken güvenli ret doğrulanır. Ayrı path check + full-path open testi bu kabulün yerine geçmez.
13. CWD A'da göreli root ile prepare, CWD B'de decoy dosyalarla validate/approve saklanan A ankrajını kullanır. Root yeni ve byte-identical dosyalar taşıyan başka inode ile değişirse ret; mutlak root kabulü, mutlak input reddi ve root override yasağı ayrı sınanır. Aynı-UID/inode-reuse/mount/rename garanti sınırı belgede korunur.
14. Prepare/validate/approve CLI ve Python'da aynı explicit config/profile/project seçeneklerini kabul eder. Custom config/nondefault profile/proje ile eşlik, seçenek verilmezse güncel config varsayılanının kullanılması, değişmiş context'te saved seçim/digest'in yeniden yazılmaması ve private secret-ref/secret snapshot'ının tek okunması doğrulanır. Marker env adı/secret plan gövdesi veya digest girdisine serialize edilmez.
15. Hash/producer/SQL kilidi sırasında en erken plan/kanıt/girdi/yetki/tahmin expiry'si tam geçilir; son UTC/monotonic örnek valid/prepared sonucu veya etkin approval yazmaz. Aynı onayı döndüren idempotent yol da reddeder. Commit gecikmesinde süre geçerse kayıt oluşabilse de etkin olmaz, çıktı bunu gizlemez ve sonraki tüketici reddeder; clock invalidation rollback/restart ile kaybolmaz.

## Doğrulama

Unit canonical digest/girdi/onay/saat; contract v1/v2 ve CLI/API; integration gerçek dosya/DB/env, iki süreç, rollback/reset/restore/legacy intent ve sızıntı. [CONTRIBUTING matrisine](../../../CONTRIBUTING.md#doğrulama-seçimi) göre tam test, Ruff/mypy/belge/ajan, wheel/sdist iki temiz kurulum ve başlangıç/cache bütçesi. Gerçek uzak auth, fiziksel güç kesintisi ve Windows bu kabulün kanıtı değildir.

## Teslim kaydı

- PR/commit: [PR #8](https://github.com/HodeTech/Yorunge/pull/8), [merge e32cb42](https://github.com/HodeTech/Yorunge/commit/e32cb4289e12a15aeb8c8037c0fca4fc6a7082aa), [hazırlık 57fe22c](https://github.com/HodeTech/Yorunge/commit/57fe22c), [onay/yönetim db9ee74](https://github.com/HodeTech/Yorunge/commit/db9ee74), [son cursor düzeltmesi e7f9039](https://github.com/HodeTech/Yorunge/commit/e7f9039).
- Sonuç: Adım 2/3 ve ikişer fresh review tamamlandı; [test/review/kurulum/ölçüm kanıtı](../../research/p01-3-implementation-validation.md). Son tam takım 1.159 test, wheel/sdist iki temiz kurulum, merge sonrası Linux cache p95 195,928 ms ve input bellek kabulü başarılı; dört adımın her biri iki fresh review turuyla tamamlandı. Kart verified; [merge/CI kapanışı](../../research/p01-3-implementation-validation.md#development-merge-kapanışı) doğrulandı.
- Kalan sınır: Public producer draft/blocked; run/operation/lease, HTTP ve gerçek EVREN yoktur. Gerçek Windows/fiziksel güç kesintisi kanıtı verilmez. Kullanıcı ürün PR'ını development'a aldı; Master aktarımı/yayın yapılmadı.
