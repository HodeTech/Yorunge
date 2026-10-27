# ADR-0004: Yerel işlemsel operasyon durumu

**Durum:** Accepted — başlangıç tasarımı. **Tarih:** 2026-10-27.

## Bağlam

Bellek içi teklifler ve yalnızca done journal'ına dayanan tekrarlar, süreç kapanması veya uzak değişiklikte güvenilir sonuç sağlamıyor. Farklı komutların aynı işlem üzerinde çalışması kalıcı sahiplik ve uzlaştırma gerektiriyor.

## Karar

Plan, operation, attempt, sahiplik ve kritik rezervasyonlar yerel SQLite transaction'larıyla tutulur. Dosya/model içeriği artefakt deposunda kalır. Sırlar DB'ye yazılmaz. Kritik kayıt yan etkiden önce oluşur; belirsiz sonuçta tekrar gönderim yerine unknown/uzlaştırma kullanılır.

[ADR-0012](0012-credential-identity-and-change-detection.md), yalnız özel yerel keyed verifier için bu sır saklama sınırını daraltmayı önerir. Henüz Proposed'dır; bu Accepted kararın istisnası yürürlüğe girmiş sayılmaz. Ham credential/hash yasağı ve diğer kayıtların sınırı korunur.

## Alternatifler

Salt RAM restart bilgisini kaybeder. JSONL gözlem için uygundur, tek başına transaction/çok süreçli sahiplik çözmez. İlk sürüm için sunuculu DB işletimi gereksizdir.

## Sonuçlar

Migration, kilit, lease/fencing, çökme ve saklama davranışı test gerektirir. SQLite uzak işlemi atomik yapmaz; sağlayıcı idempotency desteği ayrı kaydedilir. DB okunamıyorsa belirsiz yan etki güvenli biçimde reddedilir. [Veri/durum](../architecture/data-and-state.md).
