---
id: P02-4e
phase: P02
status: draft
size: M
depends_on: [P02-4d]
capabilities: [C03, C05, C13]
---
# P02-4e — Katalog CLI yüzeyi ve canlı salt okuma kabulü

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md) adım 3–4; [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) §2–§5, §9–§10; K4 (canlı okuma), K8 (UX), K11 (çıkış kodları) onaylarına bağlı.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı bir komutla Platform modellerini veya LLM modellerini tek sayfa görür, bir modeli açar ve sürüm etiketlerini ile biçimlerini öğrenir. Bugün bu komutlar yok; kullanıcı kimlikleri başka yerden kopyalamak zorundadır. Seçilen sürümün indirilmesi [P02-4f](p02-4f-selected-download-binding.md) kapsamındadır.

## Giren ve girmeyen kapsam

**Girer:**

- `models list --service evren-platform|evren-llm [--page N] [--page-size M]` (`--page` ve `--page-size` yalnız Platform; LLM’de verilirse `invalid_request`); `--task TASK` yalnız LLM (istemci tarafı filtre). `--service` zorunludur.
- `models show --service evren-platform --model OWNER/SLUG [--versions]`; `models show --service evren-platform --model-id UUID --versions` (`owner_username` null modeller için; yalnız sürüm listesi, model detayı GET’i yoktur); `models show --service evren-llm --model-id ID [--task TASK]`. Alfabe dışı kimlik `invalid_request` alır.
- `datasets list [--page N] [--page-size M]` (K2 onayına bağlı).
- Kararlı hata kodları ([ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) Karar 9, K11): `model_not_visible` (çıkış 1), `model_ambiguous`, `model_task_mismatch`, `model_not_addressable` (çıkış 2). Kodlar [CLI hata kataloğuna](../../reference/cli-contract.md#p01-5-hata-kataloğu) bu kartta eklenir; mevcut kodlar değişmez.
- Metin, JSON ve NDJSON çıktıları; ortak seçenekler `--output` ve `--non-interactive`. Profil ve proje seçenekleri yoktur; hesap aktif profilden gelir (`models download` ile aynı kural).
- Gözlem zamanı, tamlık durumu, kapsam ve sonraki komut ipucu; boş sonuç metni.
- Kanonik CLI sözleşmesi güncellemesi: [cli-contract](../../reference/cli-contract.md) komut tablosuna katalog satırları ve taslak örnekteki `yorunge llm models` yerine `yorunge models list --service evren-llm`; katalog referansı (`docs/reference/catalog.md`, P02-4c ile yazılır) (kanonik) ve kullanıcı belgesi; [C05](../../capability-matrix.md) ve [modül](../../modules/catalog-models.md) durumu.
- Kurulu wheel smoke’u ve canlı salt okuma kabulü (K4).

**Girmez:** indirme ve çözüm bağı ([P02-4f](p02-4f-selected-download-binding.md)), üç komutlu indirme yolculuğunun uçtan uca kabulü ([P02-4b](p02-4b-selected-download-acceptance.md)), P02-R10 satırı ([P02-R10](p02-r10-llm-terms-guidance.md), ayrı adım 5), kalıcı önbellek, yazma uçları, GPU/kota, görev önerisi veya sıralama, dosyaya yazma seçeneği, profil/proje seçenekleri.

## Bağımlılıklar ve kararlar

[P02-4d](p02-4d-catalog-transport-api.md) API ve taşıma. K4 canlı yetkisi yalnız salt okuma GET ve ≤20 mantıksal istek ile sınırlıdır; indirme bu kartta yoktur (K5, P02-4f). Canlı kayıt; sayılar, görev dağılımı, alan kümesi, sayfa üst sınırı ve başlık biçimlerini içerir; kimlik, ad, e-posta, adres ve anahtar değeri içermez; [kanıt standardına](../../standards/research-evidence.md) göre maskelenir.

## Sözleşme ve uygulama sınırı

- Komut adları ve seçenekler [CLI sözleşmesiyle](../../reference/cli-contract.md) tutarlıdır; kısaltma kabul edilmez.
- Metin çıktısında her değer temizlenmiş ve sınırlandırılmıştır; JSON/NDJSON her kaydı ayrı satırda ve saf biçimde verir.
- Liste çıktısı en çok bir sayfadır; tamlık `complete`, `partial` veya `unknown` olarak gösterilir; `partial` için sonraki sayfa komutu verilir. Sessiz kırpma yok.
- `--non-interactive` ve non-TTY çalışmada prompt yoktur; SIGINT ve kapalı stdout temiz çıkar.
- Yardım ve yerel komutlar katalog modülünü ve ağ kütüphanesini yüklemez (tembel yükleme).
- Yardım metni görev örneklerini yalnız örnek olarak verir; sıralama veya öneri yoktur. `owner_username` null modeller için yardım `--model-id --versions` yolunu gösterir.

## Kabul

1. Kullanıcı yolculuğu (K8a): `models list --service evren-platform` tek komutla ilk sayfayı, sayfa numarasını, tamlık durumunu, gözlem zamanını ve sonraki komut ipucunu gösterir.
2. Bulma yolu (K8b, bu kartta yalnız ilk iki adım): `models list` → `models show --versions`; owner/slug ve etiket çıktıda görünür, kimlik kopyalanmaz. Üç adımlı indirme yolunun uçtan uca kabulü P02-4b’dedir.
3. `owner_username` null model listede model kimliğiyle görünür ve `show --model-id --versions` çıkış yolu ipucunda yazılır.
4. Boş sonuç ve belirsiz çözüm metinleri “yok” veya “kaldırıldı” demez; aday listesi beş kayıtla sınırlıdır.
5. Hata ve çıkış kodları K11 sınıflamasına uyar: 401/403 çıkış 3, invalid_response çıkış 1, `model_not_visible` çıkış 1, diğer yeni kodlar çıkış 2; sır ve ham gövde hiçbir çıktıda yoktur.
6. JSON/NDJSON: stdout yalnız makine çıktısıdır; stderr’de ilerleme yalnız TTY’de vardır.
7. Gerçek süreç testleri: yardım, her çıktı kipi, eksik `--service`, LLM’de `--page`, alfabe dışı kimlik, `.`/`..` segmenti, geçersiz sayfa, SIGINT, kapalı stdout.
8. Kurulu wheel smoke’u temiz bir ortamda `models list` ve `models show` komutlarını ağsız hata yolu ve loopback sunucuyla çalıştırır.
9. Canlı (K4): Platform modelleri (liste, detay, `model_id` ile sürümler), veri setleri ve LLM listesi/detayı için GET kaydı; istek sayısı ≤20; yazma yok. Kayıt; okunan alanların canlı örnekte bulunduğunu, Platform sayfa üst sınırını, `X-Has-Next`/`X-Total-Count` biçimini, `scope` davranışını ve LLM kimlik alfabesini teyit eder. Teyit edilmeyen madde “doğrulanmadı” kalır.
10. Startup: katalog kodu import grafiğine yalnız tembel girerse yeniden ölçüm gerekmez; değişirse [startup kapısı](../../standards/performance.md) çalıştırılır.

## Doğrulama

CLI ve API için integration/süreç testleri, kurulu wheel smoke’u, Ruff, strict mypy, `check-docs.py`, `check-agent-guides.py`. Canlı kayıt ayrı bir kanıt dosyasında tutulur ve kabul raporuna bağlanır.

## Teslim kaydı

Hazırlık; uygulama ve kabul kaydı yoktur.
