# P02-0 uygulama ve review kaydı

**Tarih:** 2026-10-31. **Durum:** Araştırma/karar hazırlığı; ürün kodu, canlı kabul ve nihai PR yok. **Dal/taban:** `feat/p02-0a-sdk-pilot` / development `bc9532c`. [Teslim planı](../roadmap/p02-0-delivery-plan.md) adım/commit ve iki fresh review döngüsünün sahibidir.

## Adım 1 — P02-0a araştırma ve karar hazırlığı

Başlangıç head’i `9c4db010d60fef39f5e5971a617535e8f6a56b6c`. Kullanıcı P02-0a/P02-0b’yi tek paket ve her adımda iki fresh review turuyla yetkilendirdi; yeni ADR’de bağımlı ürün kodundan önce onay istiyor. [Kaynak/SDK/pilot araştırması](p02-contract-sdk-pilot.md), [Proposed ADR-0020](../decisions/0020-service-bound-context-discovery.md), P02-0b taslak kartı ve paket planı hazırlandı. B03/B04 çıktı/sınırları güncellendi.

İki başlangıç araştırma ajanı birbirinden bağımsız SDK kaynağını ve Platform/LLM kamu kaynaklarını inceledi. Ana inceleme sabit SDK raporu, wheel/source eşliği, kaynak boyut/hash’leri, önemli client çağrıları ve mevcut P01 kodunu tekrar kontrol etti. Bunlar formal commit-sonrası fresh review turları sayılmadı.

### Kontrol ve review durumu

İlk hazırlık kontrolü: `.venv/bin/python scripts/check-docs.py` → 134 public Markdown / 0 sorun; `.venv/bin/python scripts/check-agent-guides.py` → 6 skill / 14 kart / 0 sorun; `git diff --check` geçti. Kaynak boyut/SHA-256 listesi ve önemli endpoint/auth çağrıları scratch’teki public baytlardan tekrar karşılaştırıldı. Hazırlık commit’i ve iki fresh review turu aşağıya tamamlandıkça kaydedilir. Henüz P02-0a verified ilan edilmedi; önce bu kabul/review kapanır. Ürün testleri, build/kurulum, benchmark veya canlı EVREN çalıştırılmadı; değişiklik yalnız belgedir.

## Açık kapı ve sonraki adım

ADR-0020 Proposed; bağımlı ürün kodu onaydan önce başlamaz. Platform API key identity/raw şema ve hizmet başına yetkili live read kabulü açık; LLM principal/account introspection sunmuyor. [Kart](../roadmap/tasks/p02-0b-context-discovery.md) draft kalır. P02-0a’nın kaynak/unknown çıktısı P02-0b’yi veya P02-0 üst işini tamamlanmış yapmaz. Ayrı belge PR’ı açılmaz; nihai PR tüm paket tamamlanınca development hedefiyle açılır.
