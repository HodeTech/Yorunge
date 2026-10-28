# P01-4 uygulama öncesi inceleme

**Tarih:** 2026-10-28. **Kaynak:** `feat/p01-4-operations`, başlangıç head `fc867fc`; development `a9f1f2e`. **Durum:** Belge/kod incelemesi ve karar hazırlığı; operation ürünü uygulanmadı. [Paket planı](../roadmap/p01-4-delivery-plan.md).

## Kapsam ve yöntem

Ana inceleme ile üç bağımsız read-only ajan; state/dayanıklılık, CLI/Python/wire ve kapsam/bağımlılık/kaynak yönlerini inceledi. Ajanlar sırasıyla GPT-6 Astra high ve iki GPT-6.1 Sol high kullanmıştır. Review verisi talimat sayılmadı; öneriler mevcut kod ve Accepted sözleşmeyle karşılaştırıldı. Özel analiz arşivi inceleme/yayın girdisi değildir.

İncelenen kanonik belge grupları: current/faz P01/kart şablonu ve ready/epik PR sözleşmesi; product-scope/capability-matrix; standartlar ve ilgili Python/mimari/test/performans/hata/güvenlik; mimari overview/data-and-state/execution/integration/tool ayrımı; workflow/artifact/identity/capability modülleri; ADR-0004/0005/0011–0015; local-state/execution-plan/capability-record/scope/binding/CLI/tool-provider referansları. Önceki P01-3/PR #9 kabulü ve startup bakım kaydı yeniden uygulama kapsamına alınmadı. Kullanılan implement/plan/contract-change/review/verify skill'leri repo yönergeleriyle birlikte okundu.

Kod odağı: `application/execution.py`, execution/domain Result/error modelleri, `adapters/execution_store.py`, `state.py`, `state_schema.py`, `maintenance.py`, `capability_cache.py`, `expiry_fences.py`, public API/CLI ve en yakın execution/state/bakım testleri. İnceleme yeni runtime kanıtı değildir; mevcut 1.325 test ve bakım ölçümleri [önceki kendi kaydında](startup-ci-reliability.md) kalır. Bu hazırlıkta ürün testi/build/benchmark veya canlı EVREN/Windows/güç kesintisi testi yapılmadı.

## Doğrulanan hazırlık eksikleri ve disposition

| Konu | Mevcut kanıt / sonuç | Aksiyon |
|---|---|---|
| Kart/karar | P01-4b/4c yalnız fazdaki draft satırlardı; hazır kabul/port/wire yoktu | İki somut draft kart, dört adımlı paket ve tek Proposed ADR-0016 oluşturuldu |
| Gönderim sınırı | Mimari kayıt→lease→dış etki diyor; hangi kaydın ikinci gönderimi kalıcı kapattığı açık değildi | Tek plan operation + immutable dispatch latch; pre-arm/armed crash ve geç eski sahip kabulü önerildi |
| Approval/forget | Approval güncel satırı replace edilir; forget doğrudan plan siler, operation henüz yoktur | Tarihsel approval snapshot + plan FK/restrict/plan_in_use aynı tüketici adımında; bugünkü olmayan tüketici ürün hatası diye etiketlenmedi |
| Saat/reset | Global frontier cache/plan/approval bilir; bakım preview v2 operation fingerprint taşımaz | Lease expiry frontier tüketicisi, owner epoch ayrımı ve preview v3 önerildi |
| Restore/recover | Runtime pozitif allowlist mevcut; operation gelince eski/boş kaynakta da ret zaten Accepted | Yeni allowlist genişlemesi yapılmayacak; gerçek operation şemasıyla ret testleri ve eski intent geçiş metni gerekli |
| İş sonucu | Plan immutable draft/prepared, genel Result completed/null; execution/delivery başarı sınırı Accepted | Ayrı operation durumu ve küçük typed sonuç; jobs read dış zarfı korunacak |
| Deadline | Execution v2 gövdesinde plan expiry var; ADR-0014'ün tasarım tablosundaki tam job deadline henüz uygulanmış değil | 30 s validation/coordinator, 5 s store ve plan 300 s geçerliliği açık ayrıldı; job ömrü/provider deadline desteği iddia edilmiyor |
| Belge tutarlılığı | data-and-state uygulanmış tablo tarihçesi şema 5'i atlıyor; reference indeksinde teslim edilmiş P01-3 için kabul sürüyor deniyor | Tek kanonik güncel referansa bağlantı ve gerçek verified durumuyla düzeltildi |
| Public ürün sınırı | Producer hâlâ draft/blocked; gerçek backend/input kapanışı yok | Yeni public run ve sahte başarı eklenmez; jobs normal kurulumda boş olabilir, pozitiflik test portundan gelir |

İlk altı konu uygulanmış ürünün doğrulanmış kusuru değil, P01-4'ün gerekli yeni tüketici tasarımıdır. Ayrı state/HTTP motoru veya yeni ADR-0015 hash modeli seçmek için gerekçe bulunmadı. P01-4a ve PR #9'un mevcut kabulü yeniden açılmadı.

## Resmî kaynak kontrolü

- SQLite tek eşzamanlı writer ve kısa `BEGIN IMMEDIATE` koordinasyonunu destekler; read transaction tutarlı snapshot verir. DELETE modunda reader COMMIT'i BUSY yapabilir; FULL/IOERR/INTERRUPT sonrasında transaction durumunu varsaymak yerine açık rollback/close gerekir. [SQLite transaction](https://www.sqlite.org/lang_transaction.html), [isolation](https://www.sqlite.org/isolation.html).
- Python 3.11 `isolation_level=None` açık SQL transaction'ına uygundur; connection context manager bağlantıyı kapatmaz, executescript bekleyen transaction'ı commit edebilir. Mevcut açık yönetim korunur. [Python sqlite3](https://docs.python.org/3.11/library/sqlite3.html#transaction-control).
- Python monotonic saati geri gitmez ve sistem genelidir; yalnız farklarının anlamlı olması onu kalıcı reboot kimliği yapmaz. “Her yeni süreçte sıfırlanır” varsayımı kullanılmadı. [Python time.monotonic](https://docs.python.org/3.11/library/time.html#time.monotonic).
- SQLite atomikliği dosya sistemi/donanımın flush/kilit varsayımlarına dayanır; dış HTTP/alt süreçle aynı transaction garantisi yaratmaz. Tek gönderim latch'i bu resmî davranışlardan çıkarılan proje tasarımıdır; provider exactly-once kanıtı değildir. [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html).

Erişim 2026-10-28. Dış kaynaklar teknik alt sınırı destekler; ürün lifecycle/quota/wire seçimleri yeni ADR önerisidir.

## Onay ve sonraki adım

Somut kararlar [ADR-0016](../decisions/0016-operation-admission-and-ownership.md), exact wire [operations](../reference/operations.md), uygulama/review sırası [teslim planında](../roadmap/p01-4-delivery-plan.md). Kullanıcının “yeni ADR yazdıktan sonra onay al” talebi gereği bu paket onaylanmadan ürün kodu başlamaz. SQLite/restore yasağı gibi önceden onaylanmış kararlar için tekrar onay istenmez. Henüz yapılmamış kontrol geçmiş sayılmaz.

## Karar paketi review kaydı

İlk turda farklı iki read-only reviewer (GPT-6 Astra high, GPT-6.1 Sol high) taslağı mevcut koda/Accepted kararlara karşı inceledi. Üç P2 doğrulanıp düzeltildi:

1. Intent commit sonrası lease/generation kaybeden eski sahibin unknown bile yazamayacağı açıklaştırıldı: port çağrılmaz, CAS mümkün değilse submitted/running korunur ve yetkili takeover uzlaştırır. Commit gecikmesi ve son kontrol kaybı ayrı kabul testine eklendi.
2. Public reason_code için vaat edilen kapalı katalog somutlaştırıldı: OperationReason v1 tam değer kümesi/null/durum kuralları, exception ErrorCode ile ayrımı tek referansta yazıldı.
3. Overall/attempt/execution/delivery enum'larını literal eşitleyen cümle kaldırıldı; current/dispatched attempt seçimi, tarihsel abandoned ve terminal/teslim invariant tablosu eklendi.

Engelleyici olmayan maksimum history yükü notu kabul kapsamına alındı: full validation/reset için 262.144 geçiş sınırına kadar gerçek fixture ölçümü, quota-full nonterminal reset reddinden ayrı tutuldu. Bunun uygulanmış performans kanıtı olmadığı açık kaldı. Genel Result v1, blocked producer ve mevcut restore yasağında doğrulanmış çelişki bulunmadı.

İkinci tur farklı fresh reviewer'larla (GPT-6 Astra high, GPT-6.1 Sol high) tamamlandı. İki ek P2 doğrulanıp kapatıldı: reset clock alanını yenilediğinde tarihsel business timestamp'in gerilemesini engelleyen ret/liveness kuralı; maksimum terminal tarihçe ile normal slotu kalan karma reset yükünün iki ayrı pozitif fixture olması. Ayrıca ana incelemede admission kanıtıyla arm yetkisinin aynı approval ID/gövde olması kesinleştirildi; revoke→reapprove mevcut operation'ı canlandırmaz. Bu seçimler paketin baştaki onay özetine de işlendi.

Her iki ikinci tur reviewer'ı son revizyonları yeniden okuyup önceki maddelerin kapandığını ve yeni somut sorun bulmadığını bildirdi. Bu sonuç ürün kodu/test kabulü değildir; Proposed tasarımın belge review'udur. Son belge denetimi 113 public Markdown ve 6 skill/9 kartta sıfır sorun; git diff --check başarılı. Ürün testleri/build/benchmark bu belge hazırlığında yeniden çalıştırılmadı; önceki bakım sonuçları kendilerine ait kanıt olarak korunur.
