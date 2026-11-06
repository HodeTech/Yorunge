---
id: P02-3i
phase: P02
status: draft
size: M
depends_on: [P02-3h]
capabilities: [C03, C12, C13]
---
# P02-3i — Public resume API/CLI ve uçtan uca kesinti yolculukları

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 7. Ortak CLI/Python yüzeyi; [continuation sözleşmesi](../../reference/dataset-upload-continuation.md).

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı kesintiden sonra yalnız mevcut komutlarla kalan işi güvenle bitiremez. Teknik temel hazır olsa bile `resume` yüzeyi ve v3’ü tanıyan review/approve/show/list olmadan kullanılamaz; kök operation’ın `show` çıktısı bugün yön göstermeyen bir çıkmaz sokaktır.

## Giren ve girmeyen kapsam

`resume` (varsayılan salt okuma raporu; `--prepare` ile yerel continuation planı; `--accept-unverified-read`, `--accept-unconfirmed-effects`) için ortak API/CLI; `approve --accept-unconfirmed-effects`; v3 plan/operasyonun mevcut `review/revoke/start/list/show/reconcile` komutlarında tanınması; `unknown` kaynakların `show` metin çıktısında yerel ön kontrole dayalı “devam için” satırı (DTO değişmez); text/JSON/NDJSON; yardım metni; kapalı hata/exit eşlemesi; bounded TTY ilerleme (mevcut sayaç); rapor kota etkisi satırı; kullanıcı belgeleri (rehber, public sözleşme, CLI sözleşmesi, user-journeys, capability matrisi) girer. Native ölçüm, altı kurulum, canlı kabul ve yeni kontrat dışı keşif girmez.

## Bağımlılıklar ve kararlar

P02-3h verified olmalıdır. Yüzey adları [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) belgesinden; CLI/API değişikliği için yorunge-contract-change disiplini uygulanır (şema–tüketici–hata–belge uyumu). Karar gerekmez.

## Sözleşme ve uygulama sınırı

Yeni fiil mevcut `datasets upload` ailesindedir; ortak config/profile/state-dir seçenekleri aynıdır. Python karşılığı senkron köprü kapılarını (aktif loop/PID/thread) mevcut upload API’leriyle aynı uygular. v1/v2 çıktıları, Result v1 ve mevcut sekiz komutun davranışı değişmez. Çıktı sır, provider gövdesi, `created_dataset`, baseline ve tam yol listesi taşımaz; bounded örnek yollar (sorunlu sınıf başına ≤8, göreli, literal-secret taramalı) yalnız `resume` raporundadır. `continuation_not_possible` operation kimliğini korur ve sabit mesajla `resume` raporuna yönlendirir.

## Kabul

1. Gerçek subprocess yolculuğu: plan → start → farklı noktalarda SIGKILL → `show` (yön satırı) → `resume` (rapor) → `resume --prepare` → `review` → `approve` → `start` → `show`; kullanıcı DB düzenlemeden ve yalnız komut çıktılarıyla tamamlar; non-TTY prompt yok; JSON/NDJSON saf; hata ID’yi korur. Zincir yolculuğu: ikinci kesintiden sonra ikinci `resume`.
2. `resume` raporu uygun/uygunsuz her durumu, kapalı engelleri, sınıf sayılarını ve kota etkisini doğru gösterir; `--prepare` uygunsuzluğu `continuation_not_possible` ile reddeder; ack kuralları (`approval_required`/`invalid_request`, hem `resume --prepare` hem `approve` tarafında) ayrıdır.
3. Sentinel testleri: stdout/stderr/JSON/NDJSON/hata çıktısında provider owner/org/name, receipt, baseline, signed URL ve ham yol listesi yoktur; BrokenPipe/SIGINT/Task.cancel mevcut 6/1/6 ve ID önceliğini korur.
4. Belgeler çalıştırılan komutlarla uyumlu; çalışmayan örnek yok; v1/v2 summary DTO’ları ve mevcut sekiz komutun çıktıları değişmez.

## Doğrulama

Gerçek CLI/subprocess ve API testleri, belge ve rehber kontrolleri, Ruff, strict mypy, yorunge-contract-change denetim listesi. Kurulu wheel yolculuğu ve native/CI kabulü P02-3a’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
