---
id: P02-3i
phase: P02
status: draft
size: M
depends_on: [P02-3x]
capabilities: [C03, C12, C13]
---
# P02-3i — Public resume API/CLI ve uçtan uca kesinti yolculukları

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 7. Ortak CLI/Python yüzeyi; [continuation sözleşmesi](../../reference/dataset-upload-continuation.md).

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı kesintiden sonra yalnız mevcut komutlarla kalan işi güvenle bitiremez. Teknik temel hazır olsa bile `resume` yüzeyi ve v3’ü tanıyan review/approve/show/list olmadan kullanılamaz; kök operation’ın `show` çıktısı bugün yön göstermeyen bir çıkmaz sokaktır.

## Giren ve girmeyen kapsam

`resume` (varsayılan salt okuma raporu — uygunluk/sınıflandırma sonucu ne olursa olsun exit 0 ve `DatasetUploadResumeReport`, P02-3t’nin `resume_report` üreticisiyle kurulur; uzak envanter okunmayan veya okunamayan kaynakta `observation` null’dır, kota `capacity()` kullanımı ve denemenin ekleyeceği olarak doldurulur; `--prepare` ile yerel continuation planı; `--accept-unverified-read`, `--accept-unconfirmed-effects`) için ortak API/CLI; akış `ErrorDetails` modelinin ve üç yeniden sarma noktasının (`streams.error_payload`, `stream_results._bound`, `cli.output._bound_error`) `continuation_not_possible` için kapalı `blockers` ayrıntısını taşıması (`error_payload` ve CLI JSON stderr yolunda testli); `--prepare` hata eşlemesi (`source_active` → `operation_conflict` torun kimliği ve sonraki komutla, diğer engeller → `continuation_not_possible` kapalı `blockers` ayrıntısıyla; `pending_uncertain>0` bayraksız → `approval_required`, plan yazılmaz); rapor modunda da görülebilen hatalar `state_changed` (bağlam kaynağın projesi ya da sahibi değil), `state_busy`, `upload_plan_not_valid` (saat gözlem sırasında pencerenin dışına adım attı) ve `invalid_request` (raporun göstereceği bir yol kullanılan anahtardır) için kullanıcı metni; adı yerel yol kurallarına uymayan bir uzak öğe (ör. `CON`, `a.`, `dosya:adı`) `invalid_response` verir ve bunun için ayrı bir kullanıcı metni gerekir (“Platform arayüzünde öğeyi silin ya da adını değiştirin”; ürün onu sınıflayamaz — P02-3h karar (i): kullanıcı gevşek bir öğe tipi isterse P02-3e’nin sözleşmesi değişir, PR incelemesinde verilir); kaynak grafiği tam ise `reconcile` önerisi (`reconcile_available`); iptal edilmemiş (intent’li veya başarıyla biten) torunu olan kaynak için `source_superseded` (`related_operation_id`; `unknown` torun için `resume --operation-id <torun>`, başarıyla bitmiş için devam gerekmez); birden çok engelde tek önerilen eylem `recommended_action` ile referanstaki eylem önceliğine uyar (rapor ve `--prepare` aynı `classify`/`source_blockers`/`with_blockers` hesabını kullanır); engel varken M, M için toplam bayt ve `unconfirmed_ack_required` sınıf vektöründen türetilen bilgi amaçlı değerlerdir ve plan alanları yalnız engelsiz `selection()`dan gelir; envanter 1.024 item’ı aşınca `inventory_too_large` sabit mesajı (devam desteklenmez, uzak durumu Platform arayüzünden inceleyin); `unknown` kaynağın `show` metin çıktısında iptal edilmemiş torun varsa torunun kimliği gösterilir; lease’i dolmuş `admitted` torun için engel yerine `prepare` eylemi; `verified_only` kaynak için `source_ineligible`; v3 plan için `review` projeksiyonunun (M, seçilen bayt toplamı, istek limitleri) ve `legacy_history_only` bağlantısının v3’ü doğru göstermesi (v2 kullanıcı kapsayıcıları v3’ü taşımaz ve bu kartın işidir: `UploadIntentReview` v3’ü — `family()` doğrulayıcısı tam-Manifest limitleri varsaydığından M<N planı reddeder — ya bir v3 inceleme tipiyle ya da birleşik tiple taşır; `DatasetUploadsPage.uploads` ve `Result[DatasetUploadSummary]` dönüşleri `DatasetUploadSummaryV3`ü kabul eder; `cli/upload.py`deki `isinstance(…, DatasetUploadSummary)` noktaları (253 ve 283. satırlar) ile `adapters/upload_public.py` ve `adapters/upload_api.py`deki çalışma anı `Result[DatasetUploadSummary]` kurucuları (ve `api.py`/`cli/__init__.py` tür ek açıklamaları) ortak bir tür takma adı kullanır, aksi halde v3 özeti çalışma anında reddedilir ve operation kimliğini hata çıktısında yitirir; yorunge-contract-change disiplini); `approve --accept-unconfirmed-effects`; v3 plan/operasyonun mevcut `review/revoke/start/list/show/reconcile` komutlarında tanınması; `unknown` kaynakların `show` metin çıktısında yerel ön kontrole dayalı “devam için” satırı (DTO değişmez); text/JSON/NDJSON; yardım metni; kapalı hata/exit eşlemesi; bounded TTY ilerleme (mevcut sayaç); rapor kota etkisi satırı; kullanıcı belgeleri (rehber, public sözleşme, CLI sözleşmesi, user-journeys, capability matrisi) girer. Native ölçüm, altı kurulum, canlı kabul ve yeni kontrat dışı keşif girmez.

## Bağımlılıklar ve kararlar

P02-3x verified olmalıdır (üretici P02-3h, aşama yürütücüsü P02-3w, başlatma P02-3y, reconcile P02-3x). Yüzey adları [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) belgesinden; CLI/API değişikliği için yorunge-contract-change disiplini uygulanır (şema–tüketici–hata–belge uyumu). Karar gerekmez.

## Sözleşme ve uygulama sınırı

Yeni fiil mevcut `datasets upload` ailesindedir; ortak config/profile/state-dir seçenekleri aynıdır. Python karşılığı senkron köprü kapılarını (aktif loop/PID/thread) mevcut upload API’leriyle aynı uygular. v1/v2 çıktıları, Result v1 ve mevcut sekiz komutun davranışı değişmez. Çıktı sır, provider gövdesi, `created_dataset`, baseline ve tam yol listesi taşımaz; bounded örnek yollar (sorunlu sınıf başına ≤8, göreli, literal-secret taramalı) yalnız `resume` raporundadır. `continuation_not_possible` operation kimliğini korur ve sabit mesajla `resume` raporuna yönlendirir.

**P02-3w devri (ilerleme ve metinler).** Aşama ortamı ilerleme sayacı taşımaz: `count_upload`ın M seçilmiş dosya için bağlanması (v2 ortamı N dosyayı sayar) bu kartın işidir. `operation_uncertain` + neden `invalid_response` (confirm sayacı kabul edilen iki anlamın dışında, `created`≠1, yüklemeler birbirini çiftledi ya da presign cevabı kabul edilmedi) için kullanıcı metni gerekir: işlem “belirsiz” sayılmıştır, reddedilen aşamanın kabul edilmiş makbuzu olmadığından grafiği eksiktir ve `reconcile` onu kapatamaz; önerilen yol aynı kaynak (başarısız devam) için yeni `resume --prepare`dır (dosya uzakta görülüyorsa `observed` sınıflanır; presign reddinde hiçbir şey gönderilmemiştir).

**P02-3h devri (sürüm dağıtım listesi).** [`tests/fixtures/version-dispatch-sites.json`](../../../tests/fixtures/version-dispatch-sites.json) bu karta üç nokta atar: `upload_projection.original_summary` ve `review` ile `upload_preparation.read_approval_input` (özgün üreticinin onay girdisi okuyucusu v2 plan döndürür; bir devam planını onaylamak `approve_continuation` ile bu kartın yüzeyindedir). Kart bunları v3’ü tanıyacak biçimde günceller; liste yeşil kalmadan kapanmaz.

## Kabul

1. Gerçek subprocess yolculuğu: plan → start → farklı noktalarda SIGKILL → `show` (yön satırı) → `resume` (rapor) → `resume --prepare` → `review` → `approve` → `start` → `show`; kullanıcı DB düzenlemeden ve yalnız komut çıktılarıyla tamamlar; non-TTY prompt yok; JSON/NDJSON saf; hata ID’yi korur. Zincir yolculuğu: ikinci kesintiden sonra ikinci `resume`.
2. `resume` raporu uygun/uygunsuz her durumu (exit 0), kapalı engelleri, önerilen eylemi, sınıf sayılarını ve kota etkisini (kota dolu: kullanıcı yönlendirmesi) doğru gösterir; `--prepare` uygunsuzluğu `continuation_not_possible`/`operation_conflict` ile reddeder (`source_superseded`, `source_ineligible`, `inventory_too_large` dahil kapalı `blockers` listesinin her adı için tek cümle neden + tek sonraki adım testlidir; eylem önceliği çoklu engel fixture’ıyla sınanır); ack kuralları (`approval_required`/`invalid_request`, hem `resume --prepare` hem `approve` tarafında) ayrıdır; v3 plan `review` çıktısı M ve bayt toplamını gösterir ve doğrulamadan geçer.
3. Sentinel testleri: stdout/stderr/JSON/NDJSON/hata çıktısında provider owner/org/name, receipt, baseline, signed URL ve ham yol listesi yoktur; BrokenPipe/SIGINT/Task.cancel mevcut 6/1/6 ve ID önceliğini korur.
4. Belgeler çalıştırılan komutlarla uyumlu; çalışmayan örnek yok; v1/v2 summary DTO’ları ve mevcut sekiz komutun çıktıları değişmez.

## Doğrulama

Gerçek CLI/subprocess ve API testleri, belge ve rehber kontrolleri, Ruff, strict mypy, yorunge-contract-change denetim listesi. Kurulu wheel yolculuğu ve native/CI kabulü P02-3a’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
