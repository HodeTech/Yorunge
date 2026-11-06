---
id: P02-3o
phase: P02
status: draft
size: M
depends_on: [P02-3n]
capabilities: [C03, C13]
---
# P02-3o — İndirme native ölçümü, kanıt doğrulayıcısı ve kurulu smoke

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 13. Aktarım kabulü gerçek indirme yolunda 16/256/1.024 MiB ölçülür ([performans standardı](../../standards/performance.md)).

## Kullanıcı sonucu ve mevcut eksik

Mevcut ham akış ölçümü diske yazmaz ve upload ölçümü indirmeyi kapsamaz. İndirme yolu için bellek/süre ve doğruluk kabulü yoktur.

## Giren ve girmeyen kapsam

`benchmark-download.py`, Range/ETag destekli ölçüm sunucusu fixture’ı, native RSS B/H0/H1 yöntemi (disk yazımı, checkpoint `os.fsync` ve yayın `full_sync` pencere içinde; süreleri ayrı kaydedilir), indirme kanıt özeti/rapor türü ve `research_evidence.py verify-download-reference`, M5 çalışma zamanı kapısı ve kaynak-haritası eşliği, `evidence_privacy` bağlam eklemeleri, kalıcı arşiv girişi, kurulu smoke (installation kaydının genişletilmesi), CI iş akışı adımı ve performans standardı/CONTRIBUTING güncellemeleri girer. Upload veya raw stream ölçümlerinin değiştirilmesi girmez.

## Bağımlılıklar ve kararlar

P02-3n verified olmalıdır. Ölçüm kuralları standarttadır (U≤64 MiB, G≤8 MiB, ayrı kurulu `-I` süreç, seri, başarısız örnek saklama). Kaynak bağlı M5 referansı yalnız referans host’ta alınır; Linux sonucu tanı olarak kalır. ADR-0030 hâlâ Proposed olsa da bu referans mevcut kurallarla alınır; ADR-0030 kararı P02-7 öncesine kadar beklemeyi sürdürür. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) kabul bölümü kaynaktır.

## Sözleşme ve uygulama sınırı

Ölçüm istemcisi kurulu paketteki gerçek indirme kodunu kullanır; sunucu ayrı süreçtir ve sunucu RSS’i eklenmez. Bayt/SHA-256, istek/bağlantı sayıları, disk yazımı, fsync/link süresi ve native sayaç birimleri kayıtlıdır. Kayıt kapalı bir kanıt biçiminde arşivlenir; mevcut referans ve arşivler ezilmez. CI’da 1 GiB diske yazan indirme ölçülebilir (mevcut raw stream emsali); native referans M5’e özeldir.

## Kabul

1. 16/256/1.024 MiB için her boyutta bağımsız oracle ile bayt/SHA eşleşir, U≤64 MiB ve boyutlar arası G≤8 MiB sağlanır; başarısız örnekler saklanır, eşik yükseltilmez.
2. Kesik+devam senaryosu ölçülür ve hash doğrudur.
3. `verify-download-reference` kayıtlı kaynak/kurulum/fixture eşliğini ve eksik/eski/yabancı ortam retlerini doğrular; mevcut verifier’lar etkilenmez.
4. Altı temiz kurulumda kurulu CLI indirme smoke’u çalışır; actionlint ve CI tanımı geçerlidir; `evidence_privacy` bağlamı ve arşiv girişi doğrulanır.
5. Sonuçlar [kanıt standardına](../../standards/research-evidence.md) göre kalıcı arşive girer; CI koşusu PR aşamasında üç ortamda kontrol edilir.

## Doğrulama

Native ölçüm betiği, kanıt doğrulayıcısı ve contract testleri, kurulum/dağıtım denetimi, belge kontrolü, actionlint, Ruff, strict mypy. Eşzamanlı ağır iş olmadan seri ölçüm.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
