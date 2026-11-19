---
id: P02-4f
phase: P02
status: verified
size: M
depends_on: [P02-4e, P02-3n]
capabilities: [C03, C05, C13]
---
# P02-4f — Katalogdan seçilen sürümün ağırlık indirmesine bağlanması

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md) adım 6–7; [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) Accepted (Karar 5–6, 10). K5 (canlı indirme) için sürüm kimliği verilmedi; öneriyle “yapılmadı” kaydı alır.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı `owner/slug` ve sürüm etiketiyle bir model sürümünü seçip ağırlığını indirir; indirmeden önce hangi kimliğin çözüldüğünü görür. Bugün yalnız `--version-id` kabul edilir ([P02-3n](p02-3n-model-weights-consumer.md)).

## Giren ve girmeyen kapsam

**Girer:**

- `models download --model OWNER/SLUG --version-tag TAG` yolu; `--version-id` ile birlikte verilemez (biri zorunludur; ikisi birden argüman hatasıdır, ağ isteği yoktur). `--config`, `--profile`, `--state-dir` ve mevcut seçenekler korunur.
- `--model` yolunun sırası (ADR-0035 Karar 6). Tamamı motorun kilidi altında yürür:
  1. Argüman yargısı (adres alfabesi dahil); ağsız.
  2. Yerel ön kontroller, sürüm kimliği gerekmeden karar verilenler: hedef var (`download_output_exists`), meşgul (`download_busy`), doğrulanamayan iz (`download_partial_unverified`). Biri verilirse katalog çözümü yapılmaz ve ağ isteği yoktur.
  3. Katalog çözümü (en çok iki GET: detay ve sürüm listesi; kendi 30 s katalog bütçesi); çözülen `version_id` çıktıda gösterilir.
  4. Stage kimlik kararı (devam, temiz başlangıç, tam stage yayımı) çözülen `version_id` ile verilir; gerekiyorsa tek JSON ağırlık çağrısı (kendi 30 s bütçesi) ve motor.
- `--version-id` yolu değişmez: yerel durum kararı çözümsüz, her istekten önce yapılır; tam stage’de ağ isteği yoktur.
- Çözülen kimlik çıktısı: model kimliği, `owner/slug`, sürüm etiketi, sürüm kimliği ve biçim; “gözlemlenen kimlik” dili.
- Çözüm hataları ADR-0035 Karar 9’daki kodlarla döner; bu durumda ağırlık çağrısı ve hedef değişikliği yoktur.
- [Download-engine referansı](../../reference/download-engine.md) (model ağırlığı yüzeyi) ve katalog referansı (`docs/reference/catalog.md`, P02-4c ile yazılır) seçim bölümleri.

**Girmez:** “En son” veya varsayılan sürüm; çözümün saklanması; ZIP veya dataset öğesi indirme; lisans kabulü; sürüm oluşturma; önbellek.

## Bağımlılıklar ve kararlar

[P02-4e](p02-4e-catalog-cli-acceptance.md) çözüm kuralları ve komut yüzeyi; [P02-4d](p02-4d-catalog-transport-api.md) çözüm yardımcısı; [P02-3n](p02-3n-model-weights-consumer.md) JSON çağrısı ve motor. [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) Karar 6 seçim bağını ve kilit kapsamını belirler.

**Stage ve kimlik gerçeği** ([download-engine](../../reference/download-engine.md)): stage, sidecar ve kilit adları hedef adının hash’inden türer; aynı hedefte farklı bir sürüm `identity_key` uyuşmazlığı verir ve mevcut kurala göre yarım içerik atılır, temiz başlanır. Bu bir üzerine yazma değil, yeni indirmedir ve kullanıcıya açıkça söylenir.

**Motor ayrıştırması.** Bugün `open_sink` yerel kararı tek adımda verir ve kilit, JSON çağrısı dahil motorun callback’i boyunca tutulur. Ön kontroller (2. adım) ile kimlik kararı (4. adım) arasında çözüm çağrılarını koruyacak şekilde ayrıştırma gerekir; kilit kapsamı değişmez. Ayrıştırma P02-3l/3m’de kanıtlanmış davranışları (hedef yarışı, sidecar, kilit, resume kararı) bozmaz; mevcut kill ve resume test matrisi değişmeden geçer.

**Ödünleşme:** `--model` yolunda `identity_key` sürüm kimliğini taşıdığı için tam stage olsa bile ağsız yayım yapılamaz; kimlik doğrulaması için katalog okuması gerekir. Bu sınır referansa ve yardıma yazılır; `--version-id` yolundaki ağsız tam-stage yayımı değişmez.

## Sözleşme ve uygulama sınırı

- Çözüm yalnız [P02-4d](p02-4d-catalog-transport-api.md) yardımcısını kullanır; ayrı çözüm kodu yazılmaz.
- Çözüm hataları ADR-0035 Karar 9 sınıflamasıyla döner.
- İndirme sonucu ve doğrulama seviyesi değişmez (`transfer_complete` / `sha256_matched`); çözülen kimlik sonuçta da görünür.
- Yardım metni `--model` ve `--version-tag` için sürüm kimliğinin nereden gelmediğini ve bu yolun neyi çözdüğünü söyler; `owner_username` null modeller için `--version-id` yolunu gösterir.

## Kabul

1. Çözüm sıfır veya belirsiz ya da görev uyumsuzsa hiçbir ağırlık isteği yapılmaz (istek sayımı kanıtı); `owner_username` null ise `model_not_addressable`; detay `versions_count` ile sürüm dizisi uyuşmazsa `invalid_response`.
2. Ağsız yerel ön kontroller (hedef var, meşgul, doğrulanamayan iz) çözümden önce verilir: bu durumlarda hiç GET yapılmaz (istek sayımı kanıtı).
3. Kilit kapsamı: çözüm çağrıları sırasında kilit tutulur; eşzamanlı ikinci çalıştırma `download_busy` alır (kanıt testi).
4. Çözülen `version_id` ile tek JSON çağrısı; `--version-id` ve `--model` birlikte verilirse argüman hatası ve ağ isteği yok.
5. `--version-id` yolu ve motor davranışı regresyonsuz; mevcut kill ve resume testleri değişmeden geçer; tam stage’de ağsız yayım bu yolda hâlâ geçerlidir.
6. Çözülen kimlik çıktıda ve yardımda görünür; sürüm etiketi ile kimlik farkı açıklanır.
7. Farklı çözülen sürüm: aynı hedefte önceki kısmi içerik kurala göre atılır ve yeni indirme başlar; kill ve resume testi bu geçişi kapsar; üzerine yazma olmadığı kanıtlanır.
8. Canlı (K5): sürüm kimliği kullanıcı tarafından verilmediği için bu kartta yapılmaz; kabul “yapılmadı” olarak kaydedilir. Kullanıcı sürüm kimliği verirse ayrı tek indirme kabulü yapılır (JSON çağrısı + kimliksiz imzalı GET, seviye, bayt, süre); dosya yalnız geçici kabul hedefinde tutulur ve kabul sonunda silinir.

## Doğrulama

Integration testleri (loopback TLS, istek sayımı), süreç testleri, kill/resume matrisi (motor ayrıştırmasının regresyonu), kilit eşzamanlılık testi, kurulu wheel smoke’u, Ruff, strict mypy, `check-docs.py`. Native ölçüm bu kartta yoktur.

## Teslim kaydı

- PR/commit: [PR #18](https://github.com/HodeTech/Yorunge/pull/18) (`feat/p02-4-catalog-and-selection`, `development` hedefi; geliştirme 62300f7, R1 2d26af0, R2 bb1df34).
- Sonuç: motor iki fazlı ayrıldı (kimliksiz yerel retler ağdan önce, kimlik çözümden sonra); etiket yolu, özet `resolution` alanı (yalnız etiket yolunda), uyarı, zaman iadesi ve CLI yüzeyi testlerle kanıtlandı; `--version-id` yolu regresyonsuz. Mutasyon kanıtı: zaman iadesi, özet aktarımı ve uyarı bayrağı kaldırıldığında testler başarısız olur.
- Kalan sınır: K5 canlı indirme yapılmadı (kart madde 8). Etiket yolunda atma sonrası bir hatayla biten çalıştırma "yarım dosya atıldı" uyarısını taşımaz; `--version-id` yolu da bildirmez (belgelendi).
