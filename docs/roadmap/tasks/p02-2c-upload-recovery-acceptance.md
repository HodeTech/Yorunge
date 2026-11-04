---
id: P02-2c
phase: P02
status: draft
size: L
depends_on: [P02-2b]
capabilities: [C03, C12, C13]
---
# P02-2c — İlk upload recovery ve teslim kabulü

**Tarih:** 2026-11-02. L kapsam [planın](../p02-2-delivery-plan.md#adımlar-ve-review-döngüsü) 5–7 adımlarında ayrı commit/review/kabul birimleridir; tek kod adımı değildir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı kesinti/kayıp cevap sonrasında aynı operation ID'siyle neyin bilindiğini görür, yetkili salt okumayla uzlaştırır ve eksik kanıtı anlar. Başlangıçta yalnız generic jobs geçmişi vardı. Transfer stage/read reconciliation ve public yüzey d–w dilimlerinde yerel verified; bu üst kart son kaynak/native/kurulum/CI/ayrı canlı kabulünü kapatır.

## Giren ve girmeyen kapsam

Yerel show, kayıtlı hedefte güncel read credential ile reconcile, first-upload kill/restart/receipt kaybı, API/CLI/error/cancel ve bütünleşik kurulum/native/live/CI/kanıt girer. Etkili resume veya belirsiz isteği yeniden gönderme P02-3a'dır; bu kartta yoktur. Readonly toparlanmayı sonraki epike bırakmak, DB düzenleme, otomatik cleanup ve genel uzak stop yoktur.

## Bağımlılıklar ve kararlar

P02-2a/b gerçek kabulü; Accepted ADR-0024/0025/0026; provider exact read/correlation/item metadata eşliği ve ayrıca scoped hesap/yazma/maliyet yetkisi gerekir. Kaynak identity/key/object/URL/PII repoya girmez. Yetkisiz live başarı veya kapanmamış kanıt saklama takibiyle verified yapılmaz.

## Sözleşme ve uygulama sınırı

Dataset transfer domain/application ve adapters; CLI/Python aynı show/reconcile kullanım senaryosu. Reconcile kaydedilmiş exact target/owner/project/dataset bağını korur; güncel profil başka kaynağa yönlendirmez. Read sonucu yeni etkili permit üretmez. Metadata/byte ve v1/v2 read/ack/error seviyeleri [v2 sözleşmesinde](../../reference/dataset-upload-v2.md#read-terminal-ve-başarı-grafiği) tanımlıdır; default gerçek read grant ile yalnız açık v2 read-attempt ayrı korunur.

## Kabul

1. Create/link/presign/PUT/confirm intent ve receipt commit'lerinin önce/sonrası kill; partial PUT, SQL I/O ve response kaybında aynı operation bulunur. Sentetik uzak effect sayısı en çok bire çıkar; restart'ta create/link/presign/PUT/confirm sayısı **sıfır** olur. Admission commit'i ile ID'nin ilk çıktısı arasında kill/BrokenPipe sonrası yalnız belgelenmiş `list` ve `show --plan-id` CLI/Python yüzeyi aynı operation'ı bulur; yeni admission/permit/ağ yoktur. Intent sonrası gerçekte gönderilmemiş iş de unknown olabilir.
2. Yeni owner/fence, reset, revoke/expiry, credential rotation, ileri/geri saat ve kapasite doluluğunda eski sahibin yazısı reddedilir; read/reset recovery için ayrılmış kapasite kalır. Başka plan veya state dosyasıyla otomatik bypass yoktur.
3. Unknown create için exact correlation yoksa aday adı/id tahminiyle bağlanılmaz. Known dataset için yanlış parent/visibility/file hash/ad/adet, uzak silinme, eksik/tekrarlı/değişen sayfa ve 401/403/5xx read observation'ı kontrollüdür; yanlış terminal başarı veya retry önerisi yoktur.
4. Gerçek subprocess yolculuğunda kullanıcı plan→digest approve→start→show/reconcile adımlarını yalnız kısa yardım/metinle tamamlar. Hedef/etki/dataset-operation ID/next step ve gerçek kaynaktan taşıma byte sayacına dayalı bounded/coalesced ilerleme bulunur; provider'ın aldığı byte veya bütünlük diye sunulmaz; non-TTY prompt yoktur. Sentetik görevin 5 dakika içinde tamamlanması, yanlış hedef seçimi 0, müdahale en çok 1 ve çıktı/ID'yi 30 s içinde bulma hedefi ölçümden önce sabittir; insan UX deneyi yapılmazsa fixture başarısı onun yerine yazılmaz.
5. Text/JSON/NDJSON/UTF-8/BrokenPipe/SIGINT ve gerçek Task.cancel; belirsizlik exit 5/ID, yerel readonly sorgunun exit 0 ve explicit remote read hatasının güvenli source kodu/1 veya 3 ayrımı korunur. Kalıcı başarılı işi renderer hatası yeniden göndermeye dönüştürmez. ADR-0027 sentinel kabulü: prepare/approve/revoke/start/reconcile/list/show ve hata çıktısı internal view/receipt/created_dataset serialize etmez; reported owner_id/org_id/name canary'leri stdout/stderr/text/JSON/NDJSON/support çıktısında yoktur. Ayrı dar summary gerçek API/CLI/controller ile sınanır.
6. Gerçek streaming upload 16/256/1024 MiB, ilk ve maksimum envanter/byte/worker/queue fixture'larında exact server byte/hash oracle, native B/H0/H1/U/L, her U≤64 MiB/G≤8 MiB ve deadline kabulünü sağlar. Controller/server belleği client'tan ayrılır; tüm başarısız örnekler saklanır. 1 GiB toplam birden çok dosyada consumer limitini korur.
7. Son runtime/test/script/workflow değişikliği sonrası yeni kaynak bağlı M5 startup/jobs/dataset referansları, üç ortam tam test, lint/type/doc/skill/actionlint, wheel/sdist ve altı temiz kurulum, gerçek Linux ölçüm/receipt/witness ve kalıcı arşiv kabulü tamamdır. Ağır ölçümler seri ve yoğun dış build/test yokken yapılır.
8. Ayrı yetkili küçük canlı private create/link/upload ve aynı ID read doğrulaması exact sahiplik/dosya oracle'ıyla geçer; test sırrı/ham hesap verisi olmadan request/byte/süre/fiyat/doğrulama sınırı kanıta bağlanır. İki aynı hash farklı ad ayrıca kanıtlanır. Live eksikliği sessizce kapsamdan atılmaz.
9. Kartlar, current, matris, referans/README/changelog gerçek sonuca göre güncellenir; her adım iki fresh review/fix commit ve tek P02-2 development PR kullanıcı review'sine sunulur. Master/release/merge kullanıcıdadır.

**4 Kasım kabul 8 kısmi değişikliği:** Yukarıdaki özgün aynı-hash/farklı-ad olumlu ifade [Accepted ADR-0028](../../decisions/0028-platform-upload-content-cardinality.md) ile değiştirilir: iki farklı hash’li dosyanın tam olumlu akışı ve aynı-hash girdinin sıfır HTTP’li yerel reddi ayrı kapılardır. Özgün olumlu ihtiyaç P02-R2’de açık kalır; r4 controlled unknown sonucu pozitif kabul değildir. Diğer canlı/son kaynak/CI/kanıt kabulleri değişmez.

## Doğrulama

Contract/integration/gerçek TLS/süreç/SQLite testleri, gerçek kurulu API/CLI örnekleri ve kaynak bağlı native ölçümler. Kanıtlar [standarda](../../standards/research-evidence.md) göre kompakt rapor + kayıpsız arşiv/manifest olarak tutulur; büyük raw diff review'a taşınmaz. Ölçülmemiş UX, canlı davranış, fiziksel güç kesintisi veya donanım attestasyonu başarı diye yazılmaz.

## Teslim kaydı

Yerel d–w temelleri ve public yolculuk çalışma dalında verified; yerel tam takım/M5 native referansları geçti. Son kaynak değişikliği sonrası referans/üç ortam CI/altı kurulum ve bütünleşik canlı upload kabulü açık kalır. İlk nihai canlı deneme accepted create sonrası durdu; ayrıca onaylı salt okuma tanısı da eksik kaldı. İki tüketilmiş yetki yeni etki veya çağrı hakkı üretmez. [Güncel kabul kaydı](../../research/p02-2-implementation-validation.md) kanoniktir. P02-2b ve dış kapılar açık; draft. Bu kart verified olmadan P02-2 kapanmaz.
