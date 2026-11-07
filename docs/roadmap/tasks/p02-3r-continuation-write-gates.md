---
id: P02-3r
phase: P02
status: draft
size: M
depends_on: [P02-3v]
capabilities: [C03, C12]
---
# P02-3r — Continuation yazma kapıları, soy bağı ve M=0 geçişleri

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 5. Yaşam döngüsü ve yazma kapıları; HTTP/koordinatör P02-3h’dedir. Kimlik sırası: bu kart P02-3g’den ayrıştırıldığı için alfabetik olarak sondadır, yürütme sırası planda gösterilir (okuma yarısı P02-3g, P02-3u ve P02-3v’dir).

## Kullanıcı sonucu ve mevcut eksik

v3 geçmişi okunabilse bile continuation’ı güvenle başlatan kapılar yoktur: kaydetme, onay/iptal, admission (soy bağı, kaynak donma, dataset tekilliği), arm, makbuz, read lease, proof ve yerel durdurma/temizlik v1/v2’yi tanır.

## Giren ve girmeyen kapsam

Girer: save/approve/revoke/admit/arm/renew/receipt/stop_local/acquire_read/read_failed/prepare_initial_read/verified/cleanup kapılarının v3 için uygulanması (approve kapısı onayı P02-3f’nin saf `approve_upload_v3` işleviyle kurar, `[prepared_at, expires_at)` penceresi ve üç acknowledgement kuralı orada sınanmıştır); soy bağı ve kaynak donma (`cleanup_expired`), zincir dışı ve kaynağın torunlarında non-terminal operation yokluğu (admission transaction’ı içinde), `_namespace_available` atlaması ve kökün `intent_digest`i; durum yolu: latch ilk intent’te (v2 ile aynı; ilk intent öncesi kesinti/süre dolumu/yerel iptal → `cancelled`, kaynak değişmez), `read_failed`te v3 için açık `read_unavailable` dalı (mevcut kod yalnız v2 için bunu seçer); `verification_only` (M=0) kayıt için admission → okuma → proof → `succeeded` ve okuma hatası/kesinti/süre dolumunda `unknown`/`operation_uncertain` olmayan, kaynağın kendi kodunu taşıyan hata ve `cancelled/local_cancelled` (ADR-0031 §5 uç-durum tablosu) — bunun için mevcut kodun şu dalları v3 için açık yazılır: `prepare_initial_read` (`admitted` kabul edilir ⇔ `verification_only`), `read_failed` ve `_uncertain_verification` (latch’siz kayıtta `unknown` yazılmaz, yerel iptale gider), `stop_local` nedeni (`local_cancelled`); `--prepare` donma yolunun yalnız `running` kaynağa uygulanması (zaten `unknown` kaynağa dokunmaz, ikinci eşzamanlı `--prepare` fence/revision’ı yeniden artırmaz, `read_unavailable`/`identity_reset` nedenini ezmez) ve lease’i dolmuş unlatched `admitted` torunları `cancelled` yapması; admission’da `source_superseded` (kaynağın iptal edilmemiş torunu) denetimi; arm’ın create/link ve `file_indices` dışını reddetmesi; presign’ın öncülsüzlüğü; confirm sayacı tabanı için `N−M` değerinin kayıttan sağlanması. Girmez: HTTP, producer/koordinatör, public yüzey, DDL.

## Bağımlılıklar ve kararlar

P02-3v verified olmalıdır (okuma yarısının üç dilimi: P02-3g, P02-3u, P02-3v). [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir (2026-11-06). Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §2/§5 ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md); yeni replay, politika veya TTL yoktur.

## Sözleşme ve uygulama sınırı

Admission, onayın bağını (`validate_approval_binding_v3`) ayrıca `status == approved` ve süresi içinde olma açısından denetler; bağ geçerli ama iptal edilmiş veya süresi dolmuş bir onay admission’ı açmaz.

Mevcut clock, SQL transaction, lease/fence/CAS, kota ve hata öncelikleri yeniden kullanılır; v1/v2 yolları davranışsal olarak aynı kalır. v3 kaydı v2 gibi ilk intent’te latch’lenir (admission’da latch yoktur); `verification_only` kayıt hiç latch’lenmez; intent ve makbuz kuralları 3M ile sınırlıdır. Başarı: 3M accepted makbuz, N dosyalık ordered metadata (`TransferVerification v3`) ve kök baseline eşliği.

**P02-3g devir notu.** `StageGraphSpec.predecessor` v3’te create/link için `ValueError` verir: `arm` kapısı create/link intent’ini `predecessor` çağrısından önce ve `YorungeError` ile reddetmelidir. Depo yazıcıları (`save`, `revoke`, `_change`, `_control`, `_verified`) plan, onay, kayıt, kontrol ve kanıtı iki tiple yeniden decode eder ve bu yüzden bir devamı `state_invalid` ile reddeder; bu kapılar v3’ü adıyla ele alır (bu noktalar `tests/fixtures/version-dispatch-sites.json`da sahibi P02-3r olarak listelidir). `write_record` v3’te `dataset_id` ve `verification_only`yi sabit alan sayar ve ekleme sırasında kaydı planına bağlar; admission kaydı plan bağından kurar. `upload_repository`de sürümü “v2 değilse v1” okuyan üç nokta vardır ve v3 sessizce yanlış dala düşer (iki tipli decode şimdilik onları erişilmez kılar, decode genişletildiği anda canlanırlar): `read_failed`in unknown nedeni (`record.schema_version == 2` ise `read_unavailable`, değilse `request_uncertain`; v3 `read_unavailable` almalıdır), `_verified`ın 30 saniyelik proof tazelik penceresi (`proof.schema_version == 2` koşuluna bağlıdır; v3 proof’u da pencereye tabidir) ve başarı nedeni (`record.schema_version == 1` ise `verified`, değilse `metadata_verified`; v3 için doğru dal budur ama açıkça sınanmalıdır).

**P02-3u devir notu.** `require_created_baseline` v3’te kökün baseline’ını döner ve soyu doğrular; `arm`, `acquire_read`, `read_failed`, `prepare_initial_read`, `prepare_recovery_read` ve `_verified` v3 için bu yöntemi çağırıp detail↔baseline karşılaştırmasını yapar (`created_dataset` bir devam için hata verir, baseline’ı onun makbuzlarından aramaz). Admission, kaynağın hâlâ non-terminal ve lease’siz olduğunu ve canlı torunu bulunmadığını (`chain_snapshot` olgularıyla) aynı transaction’da yeniden doğrular (`--prepare` lease’i dolmuş `running` kaynağı önceden `unknown` yapar); yeni operation’ın `created_at`i kaynağın son olayından önce olamaz (saklı geçmişte bu kronoloji bugün denetlenmez); saklı geçmiş okunurken kaynak latch’li olmalıdır, bu yüzden `admitted`, `cancelled` ya da `verification_only` bir operation’a bağlanan devam okuma sırasında `state_invalid` olur.

## Kabul

1. Gerçek SQLite ile her geçiş ve ret: draft/expired/revoked, ack kuralları, kaynak donmamış (etkin lease) → `operation_conflict`, aynı dataset’te zincir dışı veya kaynağın torununda non-terminal operation, kaynak terminal/`admitted`, kök baseline yok; admission’da kaynağın hâlâ non-terminal ve lease’siz olması (`--prepare` ile admission arasında `reconcile` kaynağı `succeeded` yaparsa admission reddedilir); iki süreç eşzamanlı admit → tam bir kazanan; zincirde ikinci hop admission.
2. `M=0` (`verification_only`) uç-durum tablosunun her satırı: admission → proof → `succeeded`; admission → okuma hatası → kaynağın kendi kodu (exit 1/3; `operation_uncertain`/5 değil) ve kayıt `cancelled/local_cancelled`, hiçbir zaman `unknown`; admission → SIGINT/Task iptali → `request_cancelled`/6 ve `cancelled/local_cancelled`; admission → lease kaybı/SIGKILL → `cleanup_expired` ile `cancelled/lease_expired`; hiçbirinde intent yok; aynı plan yeniden başlatılamaz (yeni `resume --prepare` gerekir). `M>0`: ilk intent öncesi SIGKILL → lease dolunca `cancelled`, kaynak değişmeden kalır ve aynı kaynaktan yeniden plan M’yi aynı bulur; ilk intent sonrası → `unknown/request_uncertain`; `read_failed` v3’te `unknown/read_unavailable` (v1 dalı değişmez).
3. Arm create/link ve `file_indices` dışı indeksi reddeder; presign öncülsüz; PUT/confirm sırası, kronoloji ve tazelik v2 kuralıyla aynı; başarı eksik/fazla makbuz, eksik baseline veya N-dosya proof uyuşmazlığında yazılmaz.
4. Namespace: continuation save/admit `operation_conflict` almaz, ikinci create hakkı doğmaz; hot/full invariant kök operation’a bağlıdır.
5. Gerçek SIGKILL: admission, arm ve makbuz commit sınırlarında v3 geçmişi okunabilir kalır ve ikinci etki yoktur.
6. v1/v2 yaşam döngüsü ve golden’lar değişmeden geçer; reset (latched → unknown/identity_reset) ve revoke v3’te de tutarlıdır.
7. Donma ve dal: `--prepare` freeze yalnız `running` kaynağa uygulanır; zaten `unknown` kaynakta (neden `read_unavailable`/`identity_reset` dahil) no-op’tur ve iki süreç eşzamanlı `--prepare`’da fence/revision tek kez artar; kaynağın iptal edilmemiş torunu (intent’li `unknown`/`running`/`failed` veya başarıyla biten `verification_only`) varsa admission `source_superseded` ile reddedilir, intent’siz `cancelled` torun kaynağı bloke etmez; lease’i dolmuş `admitted` torun `--prepare`’da temizlenir.

## Doğrulama

Gerçek SQLite/süreç/fork testleri, mevcut kota/maintenance regresyonları, Ruff ve strict mypy. Ağ ve public yüzey iddiası yoktur.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
