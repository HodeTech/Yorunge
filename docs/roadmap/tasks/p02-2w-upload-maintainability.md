---
id: P02-2w
phase: P02
status: in_progress
size: M
depends_on: [P02-2u]
capabilities: [C03, C12, C13]
---
# P02-2w — Upload kaynak bakım sınırları

**Tarih:** 2026-11-03. Son kaynak dondurmasından önce iki dar kod dilimi; aynı dal/tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

P02-2 kaynak büyümesi, doğrulama ve transaction kurallarının denetlenebilir kalmasını gerektirir. Bağımsız salt okuma audit’i değişen kaynakta mevcut Sonar Cognitive Complexity eşiğini aşabilecek 12 fonksiyon ve iki tekrar grubu belirledi. Bu yaklaşık kaynak sayımıdır; çalıştırılmış Sonar veya yeni davranış kusuru iddiası değildir.

## Giren ve girmeyen kapsam

W.1 saf model/policy/URI/graph doğrulayıcılarını; w.2 repository arm/receipt, snapshot fingerprint, original hata eşlemesi ve CLI dataset dispatch’ini anlamlı yardımcı sınırlara ayırır. W.1 guarded_network.py içindeki connection deadline elapsed literal’inin üç kullanımını aynı mesajlı sabite alır; W.2 namespace SELECT/conflict çözümünü daraltır, farklı CAS UPDATE/kayıp sorgusu birleşmez. Public imza/wire, schema/DDL, golden, hata önceliği, zaman/kota/yetki veya replay politikası değiştirilmez. Değişmemiş eski HttpRequest.__post_init__ adayı bu işe eklenmez.

## Bağımlılıklar ve kararlar

U verified olmalıdır. Mevcut Accepted ADR-0024–0027 ve kanonik transfer/public/port referansları aynen uygulanır; iç refaktör yeni ADR kararı değildir. Ayrı preflight, korunacak invariants ve review dilimi sınırını doğrulamadan ready yapılmaz. V’nin ölçüm araçları ve ağır native kaynak dondurması bu karttan sonra gelir.

## Sözleşme ve uygulama sınırı

W.1: TransferRecord.state, DatasetUploadSummary.relationships, reduce_upload_policy, StorageTarget.__init__, platform_upload_literals._query, upload_store._receipt/_stages. W.2: StateUploads.arm/receipt, upload_snapshot, original _Environment.failure, cli.dispatch. V1 state kontrolleri V2 helper sırasına taşınmaz; tek decorated validator/helper ve mevcut ilk ret sırası korunur. Saf validation/helper ile I/O transaction sırası karıştırılmaz; mevcut ilk ret/hata sırası korunur. Özellikle intent COMMIT→permit, receipt+dataset atomikliği, geç receipt unknown ve tarihsel terminal grafiği aynı kalır.

## Kabul

Değişen fonksiyonlar küçük, adlandırılmış tek sorumluluklu helper’larla okunabilir; yaklaşık Cognitive Complexity≤15 hedefi bağımsız kaynak incelemesiyle tekrar değerlendirilir, gerçek Sonar kabulü nihai PR’da ayrıca izlenir. Literal/golden/semantic digest/fingerprint ve V1/V2 history sonuçları değişmez. Transaction/savepoint/deadline/credential/revoke/reset/lease yarışları, error/cancel/unknown/permit önceliği ve sıfır replay testleri geçer. Broad BaseException cleanup/uncertainty sınırları sırf kural susturmak için gevşetilmez. Her kod dilimi commit + iki farklı fresh review turu/fix teyidiyle kapanır.

## Doğrulama

W.1 domain/policy matrisleri/public summary/descriptor/URI/codec ile receipt/full-graph/history seçkilerini; W.2 journal/created-receipt writer/history/reset fingerprint/original/CLI/gerçek kill seçkilerini -W error ile çalıştırır; Ruff/tam strict mypy/doc/skill/diff. Öncesi/sonrası assertion/golden eşliği ve yan etki sırası review’de incelenir. Yeni native/live/kurulum veya üç ortam CI burada yapılmış sayılmaz; son kaynak referansları ancak tüm runtime/test/script/workflow bittikten sonra yenilenir.

## Teslim kaydı

U verified; iki eksenli preflight ve audit-bağlantı P2 fix teyidi kapandı. W.1 saf validation/URI/graph yardımcıları 734 ilk test, bağımsız diferansiyel eşlik ve iki farklı fresh turla kapandı. W.2 transaction/snapshot/CLI sınırları uygulandı; 338 ve ek139 test geçti, commit/iki fresh tur bekleniyor. Salt okunur yaklaşık audit kanıtı [aday/yöntem kaydına](../../research/p02-2-implementation-validation.md#p02-2w--kaynak-bakım-hazırlığı) bağlıdır; U.2 sınır kabulü iki fresh turla kapandı. Üst c/epik açık kalır.
