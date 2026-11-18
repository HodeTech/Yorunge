---
id: P02-4e
phase: P02
status: draft
size: M
depends_on: [P02-4d]
capabilities: [C03, C05, C13]
---
# P02-4e — Katalog CLI yüzeyi ve canlı salt okuma kabulü

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md) adım 3–4; [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) Accepted (Karar 2–5, 9–10). K4 (canlı salt okuma) ve K8 (UX) öneriyle uygulanır.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı bir komutla Platform modellerini veya LLM modellerini tek sayfa görür, bir modeli açar ve sürüm etiketlerini ile biçimlerini öğrenir. Bugün bu komutlar yok; kullanıcı kimlikleri başka yerden kopyalamak zorundadır. Seçilen sürümün indirilmesi [P02-4f](p02-4f-selected-download-binding.md) kapsamındadır.

## Giren ve girmeyen kapsam

**Girer:**

- `models list --service evren-platform|evren-llm [--page N] [--page-size M]` (`--page` ve `--page-size` yalnız Platform; LLM’de verilirse `invalid_request`); `--task TASK` yalnız LLM (istemci tarafı filtre). `--service` zorunludur.
- `models show --service evren-platform --model OWNER/SLUG [--versions]`; `models show --service evren-platform --model-id UUID --versions` (`owner_username` null modeller için; yalnız sürüm listesi, tamlık `unknown`, etiketle çözüm yok); `models show --service evren-llm --model-id ID [--task TASK]`. Alfabe dışı argüman `invalid_request` alır.
- `datasets list [--page N] [--page-size M]`.
- Kararlı hata kodları ([ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) Karar 9): `model_not_visible` (çıkış 1), `model_ambiguous`, `model_task_mismatch`, `model_not_addressable` (çıkış 2). Kodlar [CLI hata kataloğuna](../../reference/cli-contract.md#p01-5-hata-kataloğu) bu kartta eklenir; mevcut kodlar değişmez.
- Ortak seçenekler: `--config` ve `--profile` (`models download` ile aynı); `--output`, `--non-interactive`. `--project` yoktur ve reddedilir; `--state-dir` yoktur (state yazılmaz). Parser testi bu yüzeyi kilitler.
- Gözlem penceresi, tamlık durumu, kapsam etiketi ve sonraki komut ipucu; boş sonuç metni.
- Kanonik CLI sözleşmesi güncellemesi: [cli-contract](../../reference/cli-contract.md) komut tablosuna katalog satırları ve taslak örnekteki `yorunge llm models` yerine `yorunge models list --service evren-llm`; katalog referansı (`docs/reference/catalog.md`, P02-4c ile yazılır) (kanonik) ve kullanıcı belgesi; [C05](../../capability-matrix.md) ve [modül](../../modules/catalog-models.md) durumu.
- Kurulu wheel smoke’u ve canlı salt okuma kabulü (K4).

**Girmez:** indirme ve çözüm bağı ([P02-4f](p02-4f-selected-download-binding.md)), üç komutlu indirme yolculuğunun uçtan uca kabulü ([P02-4b](p02-4b-selected-download-acceptance.md)), P02-R10 satırı ([P02-R10](p02-r10-llm-terms-guidance.md), ayrı adım 5), kalıcı önbellek, yazma uçları, GPU/kota, görev önerisi veya sıralama, dosyaya yazma seçeneği.

## Bağımlılıklar ve kararlar

[P02-4d](p02-4d-catalog-transport-api.md) API ve taşıma. K4 canlı okuması yalnız salt okuma GET ile ve ≤20 mantıksal istekle sınırlıdır; yerel pilot anahtarları yalnız süreç içinde okunur, hiçbir çıktıya yazılmaz. Canlı kayıt; sayılar, görev dağılımı, alan kümesi, sayfa üst sınırı, başlık biçimleri, `scope` etkisi ve LLM kimlik alfabesini içerir; kimlik, ad, e-posta, adres ve anahtar değeri içermez ve [kanıt standardına](../../standards/research-evidence.md) göre maskelenir.

## Sözleşme ve uygulama sınırı

- Komut adları ve seçenekler [CLI sözleşmesiyle](../../reference/cli-contract.md) tutarlıdır; kısaltma kabul edilmez.
- Metin çıktısında her değer temizlenmiş ve sınırlandırılmıştır; JSON/NDJSON her kaydı ayrı satırda ve saf biçimde verir.
- Liste çıktısı en çok bir sayfadır; tamlık `complete`, `partial`, `last_page` veya `unknown` olarak gösterilir; `partial` ve `last_page` için sonraki sayfa komutu verilir. Sessiz kırpma yok.
- Boş sonuç metni: “bu anahtara görünmüyor (kesin yokluk değil)”. “Yok” veya “kaldırıldı” denmez.
- `--non-interactive` ve non-TTY çalışmada prompt yoktur; SIGINT ve kapalı stdout temiz çıkar.
- Yardım ve yerel komutlar katalog modülünü ve ağ kütüphanesini yüklemez (tembel yükleme).
- Yardım görev örneklerini yalnız örnek olarak verir; sıralama veya öneri yoktur. `owner_username` null modeller için yardım `--model-id --versions` yolunu gösterir.

## Kabul

1. Kullanıcı yolculuğu (K8a): `models list --service evren-platform` tek komutla ilk sayfayı, sayfa numarasını, tamlık durumunu, gözlem penceresini ve sonraki komut ipucunu gösterir.
2. Bulma yolu (K8b, bu kartta ilk iki adım): `models list` → `models show --versions`; owner/slug ve etiket çıktıda görünür, kimlik kopyalanmaz. Üç adımlı indirme yolunun uçtan uca kabulü P02-4b’dedir.
3. `owner_username` null model listede model kimliğiyle görünür; `show --model-id --versions` çıkış yolu ipucunda yazılır ve çalışır.
4. Boş sonuç ve belirsiz çözüm metinleri “yok” veya “kaldırıldı” demez; aday listesi beş kayıtla sınırlıdır.
5. Hata ve çıkış kodları ADR-0035 Karar 9 ile uyumlu: 401/403 çıkış 3, invalid_response ve `model_not_visible` çıkış 1, diğer yeni kodlar çıkış 2; sır ve ham gövde hiçbir çıktıda yoktur.
6. Parser: `--project` ve `--state-dir` reddedilir; `--config`/`--profile` kabul edilir; LLM’de `--page` reddedilir (süreç testleri).
7. JSON/NDJSON: stdout yalnız makine çıktısıdır; stderr’de ilerleme yalnız TTY’de vardır.
8. Gerçek süreç testleri: yardım, her çıktı kipi, eksik `--service`, alfabe dışı argüman, `.`/`..`, geçersiz sayfa, SIGINT, kapalı stdout.
9. Kurulu wheel smoke’u temiz bir ortamda `models list` ve `models show` komutlarını ağsız hata yolu ve loopback sunucuyla çalıştırır.
10. Canlı (K4): Platform modelleri (liste, detay, `model_id` ile sürümler), veri setleri ve LLM listesi/detayı için GET kaydı; istek sayısı ≤20; yazma yok. Kayıt şunları teyit eder ya da “doğrulanmadı” der: okunan alanların canlı örnekte bulunması, sayfa üst sınırı, sunucunun sayfa boyutunu düşürme davranışı, `X-Has-Next`/`X-Total-Count` biçimi, `scope` etkisi (scope’lu ve scope’suz sonuç farkı), LLM kimlik alfabesi, en büyük gerçek sayfanın boyutu (1 MiB sınırına göre).
11. Startup: katalog kodu import grafiğine yalnız tembel girerse yeniden ölçüm gerekmez; değişirse [startup kapısı](../../standards/performance.md) çalıştırılır.

## Doğrulama

CLI ve API için integration/süreç testleri, parser testleri, kurulu wheel smoke’u, Ruff, strict mypy, `check-docs.py`, `check-agent-guides.py`. Canlı kayıt ayrı bir kanıt dosyasında tutulur ve kabul raporuna bağlanır.

## Teslim kaydı

Hazırlık; uygulama ve kabul kaydı yoktur.
