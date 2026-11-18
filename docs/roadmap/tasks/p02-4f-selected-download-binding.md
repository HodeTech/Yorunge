---
id: P02-4f
phase: P02
status: draft
size: M
depends_on: [P02-4e, P02-3n]
capabilities: [C03, C05, C13]
---
# P02-4f — Katalogdan seçilen sürümün ağırlık indirmesine bağlanması

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md) adım 6–7; [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) §5–§6; K6 (sözdizimi ve motor sırası) ve K5 (canlı indirme) onaylarına bağlı.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı `owner/slug` ve sürüm etiketiyle bir model sürümünü seçip ağırlığını indirir; indirmeden önce hangi kimliğin çözüldüğünü görür. Bugün yalnız `--version-id` kabul edilir ([P02-3n](p02-3n-model-weights-consumer.md)).

## Giren ve girmeyen kapsam

**Girer:**

- `models download --model OWNER/SLUG --version-tag TAG` yolu; `--version-id` ile birlikte verilemez (biri zorunludur; ikisi birden argüman hatasıdır, ağ isteği yoktur).
- `--model` yolunun sırası (ADR-0035 Karar 6):
  1. Argüman yargısı, adres alfabesi dahil; ağsız.
  2. Ağsız yerel ön kontroller, sürüm kimliği gerekmeden karar verilenler: hedef var (`download_output_exists`), meşgul (`download_busy`), doğrulanamayan iz (`download_partial_unverified`). Bunlardan biri verilirse katalog çözümü yapılmaz ve ağ isteği yoktur.
  3. Katalog çözümü (en çok iki GET: detay ve sürüm listesi); çözülen `version_id` çıktıda gösterilir.
  4. Stage kimlik kararı (devam, temiz başlangıç, tam stage yayımı) çözülen `version_id` ile yapılır; gerekiyorsa tek JSON ağırlık çağrısı ve motor.
- `--version-id` yolu değişmez: yerel durum kararı çözümsüz, her istekten önce yapılır; tam stage’de ağ isteği yoktur.
- Çözülen kimlik çıktısı: model kimliği, `owner/slug`, sürüm etiketi, sürüm kimliği ve biçim; “gözlemlenen kimlik” dili.
- Çözüm hataları yeni kodlarla döner (`model_not_visible`, `model_ambiguous`, `model_task_mismatch`, `model_not_addressable`; sınıflama K11’e göre); bu durumda ağırlık çağrısı ve hedef değişikliği yoktur.
- [Download-engine referansı](../../reference/download-engine.md) (model ağırlığı yüzeyi) ve katalog referansı (`docs/reference/catalog.md`, P02-4c ile yazılır) seçim bölümleri.

**Girmez:** “En son” veya varsayılan sürüm; çözümün saklanması; ZIP veya dataset öğesi indirme; lisans kabulü; sürüm oluşturma; önbellek; profil/proje seçenekleri.

## Bağımlılıklar ve kararlar

[P02-4e](p02-4e-catalog-cli-acceptance.md) çözüm kuralları ve komut yüzeyi; [P02-4d](p02-4d-catalog-transport-api.md) çözüm yardımcısı; [P02-3n](p02-3n-model-weights-consumer.md) JSON çağrısı ve motor. [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) §5–§6 seçim bağını belirler.

**Stage ve kimlik gerçeği** ([download-engine](../../reference/download-engine.md)): stage, sidecar ve kilit adları hedef adının hash’inden türer; aynı hedefte farklı bir sürüm `identity_key` uyuşmazlığı verir ve mevcut kurala göre yarım içerik atılır, temiz başlanır. Bu bir üzerine yazma değil, yeni indirmedir ve kullanıcıya açıkça söylenir.

**Motor ayrıştırması.** Motor bugün `open_sink` içinde yerel kararı tek adımda verir. Ağsız ön kontrollerin çözümden önce, kimlik bağlı kararın çözümden sonra yapılması için bu fonksiyonun ayrıştırılması gerekir. Ayrıştırma, P02-3l/3m’de kanıtlanmış davranışları (hedef yarışı, sidecar, kilit, resume kararı) bozmadan yapılır; mevcut kill ve resume test matrisi değişmeden geçmelidir.

**Ödünleşme:** `--model` yolunda `identity_key` sürüm kimliğini taşıdığı için tam stage olsa bile ağsız yayım yapılamaz; kimlik doğrulaması için katalog okuması gerekir. Bu sınır referansa ve yardıma yazılır; `--version-id` yolundaki ağsız tam-stage yayımı değişmez.

## Sözleşme ve uygulama sınırı

- Çözüm yalnız [P02-4d](p02-4d-catalog-transport-api.md) yardımcısını kullanır; ayrı bir çözüm kodu yazılmaz.
- Çözüm hatası kataloğun çıkış sınıflamasıyla döner; yeni kodlar P02-4e’de CLI kataloğuna işlenmiştir.
- İndirme sonucu ve doğrulama seviyesi değişmez (`transfer_complete` / `sha256_matched`); çözülen kimlik sonuçta da görünür.
- Yardım metni `--model` ve `--version-tag` için sürüm kimliğinin nereden gelmediğini ve bu yolun neyi çözdüğünü söyler; `owner_username` null modeller için `--version-id` yolunu gösterir.

## Kabul

1. Çözüm sıfır veya belirsiz ya da görev uyumsuzsa hiçbir ağırlık isteği yapılmaz (istek sayımı kanıtı); `owner_username` null ise `model_not_addressable`.
2. Ağsız yerel ön kontroller (hedef var, meşgul, doğrulanamayan iz) çözümden önce verilir: bu durumlarda hiç GET yapılmaz (istek sayımı kanıtı).
3. Çözülen `version_id` ile tek JSON çağrısı; `--version-id` ve `--model` birlikte verilirse argüman hatası ve ağ isteği yok.
4. `--version-id` yolu ve motor davranışı regresyonsuz; mevcut kill ve resume testleri değişmeden geçer; tam stage’de ağsız yayım bu yolda hâlâ geçerlidir.
5. Çözülen kimlik çıktıda ve yardımda görünür; sürüm etiketi ile kimlik farkı açıklanır.
6. Farklı çözülen sürüm: aynı hedefte önceki kısmi içerik kurala göre atılır ve yeni indirme başlar; kill ve resume testi bu geçişi kapsar; üzerine yazma olmadığı kanıtlanır.
7. Canlı (K5): ayrı onay ve erişilebilir bir model sürümü kimliği varsa tek indirme kabulü kaydedilir (JSON çağrısı + kimliksiz imzalı GET, seviye, bayt, süre); dosya yalnız kabul için ayrılmış geçici hedefte tutulur ve kabul sonunda silinir. Onay yoksa “yapılmadı” kaydı yazılır.

## Doğrulama

Integration testleri (loopback TLS, istek sayımı), süreç testleri, kill/resume matrisi (motor ayrıştırmasının regresyonu), kurulu wheel smoke’u, Ruff, strict mypy, `check-docs.py`. Native ölçüm bu kartta yoktur; canlı indirme yapılırsa bayt, süre ve seviye kaydedilir.

## Teslim kaydı

Hazırlık; uygulama ve kabul kaydı yoktur.
