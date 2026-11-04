---
id: P02-2b
phase: P02
status: draft
size: M
depends_on: [P02-2a]
capabilities: [C03, C12, C13]
---
# P02-2b — Bounded dosya gönderimi ve doğrulanmış confirm

**Tarih:** 2026-11-02. [Paket planı](../p02-2-delivery-plan.md), [taslak referans](../../reference/dataset-transfer.md).

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı doğru private dataset/proje için izinli storage hedefine dosyalarını bounded olarak gönderir; her dosyanın uzak karşılığını ve doğrulama seviyesini görür. Genel HTTP bytes request'i ≤1 MiB olarak korunur; ayrı storage portu f ile çalışma dalında verified, gerçek presign/confirm codec/producer ve ortak workflow d–w dilimlerinde yerel verified; üst teslimin nihai kabulü açıktır.

## Giren ve girmeyen kapsam

API proxy/direct signed target ayrımı, exact allowlist/header/expiry, descriptor byte kaynağı, en çok 2 worker/2 MiB byte kuyruğu, strict presign/PUT/confirm codec ve ad/hash/size/cardinality karşılaştırması girer. Otomatik replay, presign yenilemesi, cross-origin auth, genel download/Range, ZIP/import, public/silme ve ileri resume girmez.

## Bağımlılıklar ve kararlar

P02-2a gerçek current/intent kabulü ve Accepted [ADR-0025](../../decisions/0025-isolated-storage-streaming.md)/[0026](../../decisions/0026-explicit-unverified-transfer-attempts.md) gerekir. Default verified_only ile açık explicit_attempt risk/onay kapıları ayrı korunur. Mevcut proxy/strict consumer çalışma dalında yerel uygulanmıştır. [Accepted ADR-0028](../../decisions/0028-platform-upload-content-cardinality.md) ilk yolu tekil SHA-256’lı dosya kümeleriyle sınırlar; tekrarlar prepare/approve/yeni start öncesi yerel ret olur. Direct provider hedef/expiry/header ve aynı hash/farklı adın olumlu uzak desteği P02-R2’de açık; bu ilk yol için destek iddia edilmez. Son olumlu live/native/CI kabulü henüz kapanmadı. Depolama yanıtı kendi hedef allowlist'ini yetkilendiremez.

## Sözleşme ve uygulama sınırı

Domain hedef/byte/receipt tipleri, application transfer state machine, somut HTTPX/file adapter; CLI/Python aynı application yolu. [Transfer referansı](../../reference/dataset-transfer.md) provider kaynak/tip/sınır/başarı oracle'ını tek yerde tutar; [HTTP referansının](../../reference/http-transport.md) mevcut kullanıcıları gevşetilmez. Signed URL hiçbir public/persisted tipe girmez.

## Kabul

1. İki ayrı TLS origin ile API key yalnız bound Platform proxy'ye gider; direct signed storage'da platform/LLM key, auth/cookie/proxy veya client default yoktur. Private/loopback/link-local/mixed DNS, DNS rebinding ve peer uyuşmazlığı; redirect, wrong port/path/host, hedef değişimi, expiry ve prepared URL uyuşmazlığı sıfır yeni etkilidir.
2. Kısa/uzun secret, signed query/header canary; raw metadata, stdout/stderr/JSON/NDJSON/log/repr/exception/DB/receipt ve cancel yollarında kapsamlı literal denetim geçer. Muaf sabit protocol alanları genel secret detector iddiası üretmez.
3. Bounded descriptor streaming byte/hash ve Content-Length, kısa okuma, aynı boyutlu değişim, root/ancestor değişimi ve byte/worker/queue sınırları gerçek HTTP yolunda doğrulanır. Gönderilen hash uyuşmazlığında confirm yoktur; geçici nesne kalabilir.
4. ADR-0028: tekrarlı SHA-256 manifesti yerel preflight’ta upload_duplicate_content/2, sıfır HTTP/etki; yerel Manifest/input adları korunur. Tekil hash’li işlerde presign ve confirm bijeksiyonu her dosya adı/size/hash/index'ini korur; duplicate/eksik/fazla/yanlış key veya dataset, mantıksal hata 2xx, metadata ETag/nullable hash ve aynı hash farklı adlarda yanlış success yoktur. Desteklenmeyen adı flatten/skip yapmak yasaktır.
5. Her etkili aşamada durable intent + tek permit + tek HTTP denemesi vardır. Timeout/connection-refused/429/5xx otomatik PUT/presign/confirm üretmez; işlem ve kalan durum korunur. İki worker'dan biri durduğunda yeni arm/confirm açılmaz; diğerinin önceden arm edilmiş/in-flight intent'i kendi receipt/unknown kaydıyla gözlenir, rollback varsayılmaz.
6. Tek session/client/pool için toplam iki connection/keepalive ve iki slot; query `%2F/%2B/%3D` exact wire kabulü/path escape reddi, missing direct origin, identity encoding ve 16 KiB URL/64 KiB PUT response aşımı, yetki taşıyan object key saklanmaması; strict response/total/phase sınırı, yavaş disk/throttle ve cleanup ve Task.cancel yayılımı gerçek async/TLS testte geçer. Yerel iptal uzak iptal veya onaylı ikinci gönderim değildir.

## Doğrulama

Contract/loopback TLS/descriptor/process testleri ve byte sayan bağımsız server oracle'ı; mevcut secret/HTTP/execution regresyonları. Gerçek 16/256/1024 MiB upload-native bellek/süre ve kurulu/final source kabulü P02-2c'nin bütünleşik sahibidir; mevcut raw download testi burada başarı yerine geçmez. Canlı çağrı yalnız paket planındaki ayrı onayla yapılır.

## Teslim kaydı

Yerel f storage ve g–k v2 temeli çalışma dalında verified; gerçek provider codec/current producer/public ve bütünleşik/live kabul eksik, üst kart draft.
