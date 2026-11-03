---
id: P02-2s
phase: P02
status: in_progress
size: M
depends_on: [P02-2r]
capabilities: [C03, C12, C13]
---
# P02-2s — Aynı upload kaydında salt okuma uzlaştırması

**Tarih:** 2026-11-03. Aynı P02-2 dalı/tek nihai development PR’ı; API/CLI public yüzey sonraki dar teslimdir.

## Kullanıcı sonucu ve mevcut eksik

Original invocation artık metadata proof’u kalıcılaştırabilir. Durmuş tam write grafiğinin yeni bir çağrıda, güncel credential ve aynı exact uzak kaynakla yalnız okunarak doğrulanması henüz gerçek composition’a bağlı değildir. Bu kart o yolu tamamlar; missing receipt veya bilinmeyen create için success uydurmaz.

## Giren ve girmeyen kapsam

Yerel preflight/expired cleanup, deferred config/env/current binding, gerçek mandatory read, read-only lease/takeover, items/proof, source hata/iptal ve aynı-ID sonuç girer. Root/manifest dosyası açma/hash, original write access, intent/permit, presign/PUT/confirm ve devam ettirilen upload yoktur. Public summary/API/CLI/sentinel ve native/kurulum/source CI/live ayrı kabul olmaya devam eder; bu ayrım epik kapsamını düşürmez.

## Bağımlılıklar ve kararlar

P02-2r üç dilim/ikişer fresh turla yerel verified; p/q/o/k read/receipt/current temeli verified. Accepted ADR-0024/0025/0026/0027 ve [v2 read matrisi](../../reference/dataset-upload-v2.md#read-terminal-ve-başarı-grafiği) değişmez. [Uzlaştırma composition referansı](../../reference/dataset-upload-reconciliation.md) implementasyon öncesi daraltmadır. Yeni grant, fiyat, replay veya temel karar yoktur; Sol/high contract ve Astra/high safety belge/kod preflight’ı temiz tamamlandı; yeni ADR veya açık temel karar yoktur.

## Sözleşme ve uygulama sınırı

Somut credential/state/session/provider dış adapter’dadır; application read algoritması CLI’dan bağımsızdır. Önce yerel kayıt/ownership/baseline/graph/insan seçimi kapıları uygulanır; loader bundan sonra çağrılır. Current scope tarihsel store/target/owner/project niyetini korur; açık current profile seçimi ve credential/epoch/generation güncel olabilir. SQLite fazları kısa, await boyunca kapalıdır. Public caller proof/producer/client enjekte etmez; internal receipt/view/baseline çıktı değildir.

## Kabul

Tam accepted graph’lı unknown kayıt, read flag ve current credential ile gerçek TLS metadata okuyup aynı operation ID’de metadata success olur; authority/remote bytes kanıtı üretilmez. Rotation/reset sonrası historical scope/baseline immutable, proof current scope’tadır. Terminal, etkin owner, legacy v2 baseline, unlatched/missing ID/incomplete graph ve flag retleri config/env/source/network/lease öncesi kendi önceliğiyle kapanır. Expired local cleanup yeni hak değildir. Mandatory veya items 401/403/429/5xx/schema/timeout ayrı readonly source code/1 veya 3 + ID, unknown/read_unavailable; yerel owner/scope/clock/quota retleri kendi güvenli kodlarını korur. Gerçek Task.cancel cleanup sonrası yayılır; SIGINT yerel request_cancelled/6’dır. Commit/kill/cevap kaybında terminal düşmez, sonraki çağrı ikinci write üretmez. Ayrı readonly toplam bütçe 30 s, mevcut request/byte/read retry tavanları ve bounded pool kullanılır.

## Doğrulama

Gerçek loopback TLS + SQLite/credential registry/reset/clock ve process-kill; loader/env/source/hash/HTTP trap’ları; read-only meter ve no-write assertions; eski read/recovery/receipt/history regresyonları. Ruff/strict mypy/doc/rehber/diff. Kod commit → fresh R1/fix → farklı fresh R2/fix kapanır. Hesap çağrısı/native/kurulum/CI bu kartın kabulü değildir; yeni live yetkisi çıkarılmaz.

## Teslim kaydı

İki eksenli preflight temiz. S.1 local/current/probe iki fresh kod turu ve iki P2 fix teyidiyle yerel kapandı; s.2 read lease/items/proof açık; r’nin original success’i bu ayrı restart/read tesliminin kabulü sayılmaz. İki cohesive kod dilimi: s.1 ağsız preflight + deferred current binding + gerçek mandatory read gözlemi (lease/proof yok); s.2 read lease/items/proof + source hata/iptal/rotation/kill tam uzlaştırma. Her dilim ayrı commit ve iki fresh turla kapanır; s.1 gözlemi public success değildir.
