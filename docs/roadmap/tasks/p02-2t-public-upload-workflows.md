---
id: P02-2t
phase: P02
status: in_progress
size: M
depends_on: [P02-2s]
capabilities: [C03, C12, C13]
---
# P02-2t — Ortak upload CLI ve Python yüzeyi

**Tarih:** 2026-11-03. Aynı P02-2 dalı/tek nihai development PR’ı. Üç kod dilimi, her dilimde commit ve iki farklı fresh review turu.

## Kullanıcı sonucu ve mevcut eksik

Private prepare/approve/original/reconcile bileşenleri gerçek TLS/state sınırlarında çalışır. Kullanıcının bunları normal CLI/Python API ile kullanması, seçtiği niyeti onaydan önce incelemesi ve sonucu/recovery kimliğini bulması henüz bağlı değildir. Bu kart public yüzeyi tamamlar; native/live/üç ortam son kaynak kabulü üst c kartında sürer.

## Giren ve girmeyen kapsam

Dar tipli summary/history ve ayrı yerel requested-intent incelemesi; sekiz ortak API/CLI işlemi; exact argüman/context seçimi; UTF-8 text/JSON/NDJSON; digest/ack ve etkileşimsiz kullanım; TTY’de gerçek kaynak byte ilerlemesi girer. Raw receipt/view/create baseline/grant/cost injection, yeni yetki/fiyat oracle’ı, replay/resume, otomatik prompt/şart kabulü, yeni canlı çağrı veya büyük kaynak ölçümü girmez.

## Bağımlılıklar ve kararlar

S verified olmadan kod başlamaz. Accepted ADR-0024–0027 ve [public sözleşme](../../reference/dataset-upload-public.md) uygulanır. Henüz yayımlanmamış summary’ye operation satırından dataset ID ve saved approval durum/tarihi eklenmesi; ayrı requested-plan review DTO’su, temel güven/izin/receipt kararını değiştirmeyen kullanıcı yüzeyi tamamlamasıdır. Provider-reported owner/org/name yayımlanmaz. Belge preflight iki eksende tamamlanmadan ready yapılmaz; temel karar gerektiren yeni bir değişiklik çıkarsa önce kullanıcıya sunulur.

## Sözleşme ve uygulama sınırı

T.1 typed projection + yerel list/show/review/revoke; t.2 gerçek prepare/approve/start/reconcile API kompozisyonu; t.3 parser/render/TTY ilerleme. Application/domain kuralı CLI’ya kopyalanmaz; API ve CLI aynı kullanım senaryolarındadır. Kaydedilmiş plan bağlamı deferred çözülür; local lookup/recovery env/hash/ağdan önce kalır. Public caller client/factory/clock/producer/proof alamaz.

## Kabul

Summary ve requested-intent DTO strict/kapalı; v1 history korunur, yeni v1 write kapalıdır. List keyset/byte tavanında satır atlamaz ve tek snapshot’tır. Prepare→review→digest approve→start→show/reconcile gerçek public API ve CLI ile çalışır. Unknown/default authority/cost dürüst, acknowledgement exact’tir. User-picked metadata ve provider-reported baseline kaynakları karıştırılmaz; receipt sentinel değerleri text/JSON/NDJSON/stdout/stderr/hata zincirinde yoktur. Active-loop/yanlış argüman/source/local/ID/terminal/kill/BrokenPipe/SIGINT/Unicode/duplicate seçenek ve non-TTY retleri anlamlı testlerle kapanır. Progress en çok 10 Hz, sadece text+TTY stderr, source bytes ile confirmed bytes ayrı; makine çıktısına karışmaz.

## Doğrulama

T.1 golden/type/strict/projection/keyset ve gerçek SQLite; t.2 gerçek TLS/state/API/rotation/no-source/recovery; t.3 gerçek subprocess/stdio/PTY ve önceki CLI regresyonları. Her dilimde uygun Ruff/strict mypy/doc/rehber/diff; commit + fresh R1/fix + farklı fresh R2/fix. Full suite/native/kurulum/source CI/kanıt/live üst c sahibindedir; burada yapılmış gösterilmez.

## Teslim kaydı

S yerel verified; public sözleşme preflight iki eksende ve iki P2 düzeltme teyidiyle kapandı (333cf16). T.1 uygulaması başladı. Yeni canlı write yetkisi yoktur. Gerçek public kod ve iki fresh kod turları henüz yapılmadı.
