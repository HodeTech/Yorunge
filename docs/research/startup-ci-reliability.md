# Başlangıç ölçümü güvenilirliği ve CLI bakım kabulü

**Tarih:** 2026-10-28. **Durum:** Uygulandı ve yerelde doğrulandı; yeni workflow'un GitHub çıktısı sonraki P01-4 PR/merge akışında incelenecek. **Dal:** feat/p01-4-operations. **Kaynak:** runtime cabb36b, ölçüm/CI 7462103; taban development@a9f1f2e. P01-4 ürün implementasyonu bu çalışmanın kapsamında değildir.

## Sorun ve sınır

PR #9'un son PR koşusu Intel Xeon 8573C'de cache p95 192,217 ms ile başarılıydı. Aynı kaynak ağacı/wheel development merge'ünde AMD EPYC 7763'te 218,223 ms gördü; [ham kayıt](evidence.md#p01-3-followup-merged-startup) korunur. [GitHub'ın ikinci merge denemesi](https://github.com/HodeTech/Yorunge/actions/runs/40693146816/attempts/2) 200,926 ms ile yine başarısızdır; bu bakımda yeni uzak koşu başlatılmadı. Kod eşitliği, farklı host'ların aynı mutlak süreyi vereceğini kanıtlamaz. [Önceki merge ve CI kaydı](p01-3-implementation-validation.md#pr-9-development-merge-kapanışı) tarihseldir.

Kabul hedefleri değişmedi: help/version 500 ms, context/cache 200 ms ve cache için 1.024 gerçek sentetik kayıt. Tabanın kötü sonucu veya göreli iyileşme bu kapıyı aşan adayı başarılı yapmaz. Yeni fiziksel runner kurulumu veya repository koruma değişikliği bu işin çıktısı değildir. Mevcut 5 saniyelik state bütçesi, doğrulama ve dayanıklılık kuralları korunur.

## Uygulanan değişiklik

CLI, bütün komutların seçenek ağacını her çağrıda kurmak yerine seçilen komut ailesini ilk parse/help sırasında oluşturur. Kök yardımında bütün komut adları korunur. Parent seçeneklerin önceliği, tekrar parse, state-dir konumları, gerekli leaf argümanları ve abbreviation reddi sınandı. API/domain/SQLite ve frozen v1 şemalarında değişiklik yoktur. Özellikle Pydantic doğrulaması veya clock/expiry/commit kapıları kaldırılmadı.

`scripts/check-startup.py`, her tarafın frozen runtime gereksinimleriyle ayrı wheel/venv kurar ve import kökenini doğrular. Test araçları, kullanıcı site paketleri ve ambient Python seçenekleri ölçüm ortamına taşınmaz; sentetik süreçlerin hash seed'i sabittir. Hazırlık/kurulum ve fixture üretimi zamanlanan CLI sürecinden öncedir. Her tarafın profili aynı baytlardır; fixture sayısı/payload hacmi eşittir ve state dizinleri ayrıdır. Bütün süreçler kaynak import yolu eklenmemiş yeni benchmark çalışma dizininde başlar.

`scripts/benchmark-startup.py` v2, taban/adayı tek host'ta AB/BA sırasıyla dönüşümlü çalıştırır. Her taraf için ilk süreç ayrı, ardından üç ısınma ve 30 ölçüm vardır; yavaş örnekler elenmez. p95 ve eşik kararındaki örnekler tam hassasiyetle saklanır. CPU/runner image/affinity, runtime paket sürümleri, wheel ve kaynak hash'leri kaydedilir; ölçüm boyunca kaynak değişimi helper'ı başarısız yapar. Rapor/çalışma dizini no-clobber korunur. [Kanonik yöntem ve kabul](../standards/performance.md#aynı-makinede-başlangıç-karşılaştırması).

CI aynı helper'ı PR ve push'ta kullanır. PR base SHA'sı veya push öncesi SHA ayrı checkout'a sabittir; fallback aynı kaynak kontrolüdür. Yalnız belge içeren ilk release tabanı açık durumla raporlanır, adayın mutlak kapıları çalışır. Ubuntu 24.04 etiketi ana OS sürümünü sabitler; image build'i, fiziksel CPU ve VM yükü değişken kalır. Bu düzenleme farklı makineler arasında kesin süre eşitliği vaadi değildir.

## Gerçek eşli ölçüm

[Ham A/B kaydı](evidence.md#startup-ci-paired), a9f1f2e tabanı ile 7462103 adayını ayrı yeni runtime ortamlarında ölçer. Apple M5 Max, macOS 27.0.1, APFS/SSD, CPython 3.11.18; aynı yedi runtime paketi, 1.024 kayıt/1.212.625 payload baytı/en büyük 1.233 bayt. Test/build/profiler işi ölçümle eşzamanlı başlatılmadı. Her komut için 30 çiftin tamamı ve kaynakların değişmediği kanıtı kayıttadır.

| Komut | Taban p95 (ms) | Aday p95 (ms) | Eşli medyan aday/taban oranı | Aday daha hızlı çift |
|---|---:|---:|---:|---:|
| Help | 26,900 | 24,297 | 0,929054 | 29/30 |
| Version | 25,615 | 22,594 | 0,924737 | 30/30 |
| Context | 76,454 | 83,854 | 0,987032 | 22/30 |
| Cache | 115,898 | 114,306 | 0,985294 | 27/30 |

Aday bütün mutlak bütçeleri geçti. Help/version için bu koşuda eşli medyan yaklaşık %7 azaldı; cache kazancı yaklaşık %1,5 ile küçüktür. Context p95 bu koşuda yükselmiştir; eşli medyanın azalması bu kuyruk gözlemini silmez. Bu sonuçlardan bütün komutların p95'inin kalıcı iyileştiği veya Linux merge hatasının kesin çözüldüğü çıkarılmaz.

[A/A kontrolünde](evidence.md#startup-ci-control) aynı 7462103 kaynağı iki yeni ortama kuruldu; iki wheel SHA-256'sı da `072efd7c3aac4c751ce9ca29af833d707a9d1b94aaf272326f8cd047893bf76f`. Cache eşli medyan oranı 0,999343 ve daha hızlı çift 15/30'dur. Taban/aday cache p95 121,045/123,006 ms; context 97,560/85,229, help 92,263/57,377 ms'dir. Aynı kodda bile kuyruk süreleri oynayabilir; bu kontrol gürültüyü görünür kılar ve A/B'deki küçük etkileri aşırı yorumlamayı önler. Tüm örnekler korunur, A/A da dört mutlak bütçeyi geçti. OS/disk cache'i fiziksel olarak boşaltılmadı ve host'un arka plan yükü tamamen yalıtılmadı.

## Doğrulama ve kalan dış kabul

- Tam yerel takım **1.325 passed (172,40 s)**. Son helper kontrolleri ayrıca **24 passed (1,11 s)**; Ruff format/lint ve strict mypy 43 kaynakta geçti.
- 30 ayrı CLI yardım çıktısı development tabanıyla bayt düzeyinde eşleşti. Yeni parser testleri seçilmemiş ailelerin yüklenmediğini ve mevcut parse/hata sözleşmesini doğrular.
- Ölçüm testleri AB/BA sırasını, bütün 30 örneğin korunmasını, daha hızlı ama 200 ms üstündeki adayın reddini, 200,0001 ms'nin yuvarlanarak geçememesini, eksik baseline/aynı state/farklı veri veya profil reddini sınar. Source değişimi, alt süreç hatası, temiz ortam ve no-clobber negatifleri eklendi. Testlerdeki sabit süreler kontrol akışıdır, performans kanıtı değildir.
- Son build wheel 42/sdist 269 üyeyle iki temiz kurulumda origin/metadata/v1/cache/execution smoke'larını geçti. Runtime wheel SHA-256'sı iki gerçek ölçümde de aynıdır; sonraki yalnız belge/ham kayıt kapanışı sdist girdisini değiştirir.
- İki gerçek ölçümün JSON p95'leri 30 örnekten yeniden hesaplandı; paket sürümleri ve kaydedilen bütün aday kaynak hash'leri checkout ile eşleşti. Gerçek EVREN, yeni Linux runner, fiziksel güç kesintisi veya Windows performansı sınanmadı.

Kullanıcı tercihiyle bu bakım için ayrı PR/merge açılmaz ve GitHub koşusu beklenerek çalışma bloklanmaz. Değişiklikler P01-4 dalında tutulur; yeni workflow'un Linux çıktıları P01-4 bitimindeki PR/merge'de ayrıca değerlendirilir. Eski merge koşusunun kırmızı sonucu korunur; dış CI performans takibi bu yerel sonuçlarla yeşile çevrilmiş sayılmaz. P01-4b/4c draft kalır.

## Yöntem kaynakları

[GitHub hosted runner açıklaması](https://docs.github.com/en/actions/concepts/runners/github-hosted-runners), [uv frozen/runtime sync açıklaması](https://docs.astral.sh/uv/concepts/projects/sync/) ve [Pydantic performans açıklaması](https://docs.pydantic.dev/latest/concepts/performance/), 2026-10-28'de incelendi. Bunlar yöntem bağlamıdır; yukarıdaki süreler kendi ham ölçümlerimizdir. Genel `defer_build` deneyi önceki kayıtta anlamlı kazanç göstermediği için bu uygulamaya eklenmedi.
