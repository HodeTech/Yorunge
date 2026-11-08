---
id: P02-3n
phase: P02
status: draft
size: M
depends_on: [P02-3m, P02-0d]
capabilities: [C03, C05, C13]
---
# P02-3n — Model ağırlığı tüketicisi ve `models download` yüzeyi

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 13. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) §1; kesin sürüm kimliğiyle ilk gerçek tüketici.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı bir model sürümünün ağırlığını (kesin sürüm kimliği ve biçim) güvenli, no-clobber ve doğrulama seviyesi görünür biçimde indirebilmelidir. Bugün model ağırlığı indirme yoktur. Sürüm kimliğini kullanıcı Platform arayüzünden alır (katalog çözümü P02-4’tedir).

## Giren ve girmeyen kapsam

`GET models/versions/{id}/download` JSON çağrısının strict codec’i; isteğe bağlı `fold` parametresi; `download_url` hedef türetmesi ve doğrulaması; ortak motor kompozisyonu; `api.download_model_weights` ve `models download` komutu (text/JSON/NDJSON, yardım — sürüm kimliğinin nereden alınacağı dahil —, hata eşlemesi); referans, CLI sözleşmesi, kullanıcı rehberi ve yetenek matrisi girer. **Başlangıç kapısı** P02-3j’dedir (yoklama motor kodundan önce yapılır; ADR-0032 §1). Olumsuz sonuçta (oturum isterse) bu kart yüzeysiz iç tüketici olarak kalır (CLI/API yüzeyi kurulmaz); yoklama yapılamadıysa tüketici “canlı doğrulanmadı” etiketiyle teslim edilir. Katalog araması/sürüm çözümü (P02-4a), ağırlık uygunluğu, lisans/şart kabulü, ZIP/dataset öğesi indirmesi girmez.

## Bağımlılıklar ve kararlar

P02-3m verified olmalıdır; Platform bağlamı P02-0d’dedir. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) Accepted’dir (2026-11-06). Yoklama kapısı P02-3j öncesinde yapılır; kullanıcının erişebildiği bir model sürümü kimliği ve ayrı yetki gerekir, yoksa kapı “yoklama yapılmadı” olarak kayda geçer. CLI/API için yorunge-contract-change disiplini uygulanır.

## Sözleşme ve uygulama sınırı

[indirme motoru sözleşmesi](../../reference/download-engine.md) içindeki yüzey. JSON çağrısı yalnız kayıtlı Platform kimliğiyle ve ADR-0017 salt okuma politikasıyla yapılır; `download_url` kayıtlı Platform origin’inde ve tam olarak `{api_base_path}/files/evren-models/` önekinde (yanıt genişletemez), https/443, userinfo/fragment/dot-segment olmadan ve ≤16 KiB olmalıdır; sağlayıcının `filename` alanı çıktı adı olmaz. Beklenen özet yalnız kullanıcının `--sha256` değeridir. Erişim/lisans/şart engeli `remote_access_denied`/3’tür ve şartlar kabul edilmez.

## Kabul

1. Loopback TLS: JSON çağrısı `X-API-Key` taşır, indirme taşımaz; yanlış origin, önek (başka bucket dahil), http, userinfo, fragment, `..`, aşırı URL, eksik/yanlış tipli alan, sağlayıcı filename’inin yol ayırıcı içermesi ve 401/403/404/429/5xx hepsi imzalı URL isteğine geçmeden kontrollü ret verir (`{api_base_path}/files/` dataset bucket yolu ve API tabanı olmayan `/files/evren-models/` dahil); `fold` verilirse iletilir ve kimlik anahtarına girer.
2. `--sha256` eşleşirse `sha256_matched`/`user_supplied`, yoksa `transfer_complete`; uyuşmazlık exit 7 ve hedef yok; seviye çıktıda doğru ve fazla iddiasız; `--fold`, `--timeout`, `--sha256` değer alanları strict doğrulanır; yardım metni `--timeout` için 1 GiB’ın varsayılan 900 s’de ~9,5 Mbit/s payload gerektirdiğini gösterir.
3. JSON/NDJSON saf, TTY ilerleme yalnız stderr, BrokenPipe/SIGINT/Task.cancel mevcut 6/1/6 ve ID önceliği; sentinel testleri imzalı URL/query/ETag/filename sızıntısı olmadığını gösterir.
4. Kurulu CLI yolculuğu: yardım, yanlış format, var olan hedef, yarım indirme sonrası aynı komutla devam; tam-stage bırakılmışsa komut hiçbir ağ isteği (JSON çağrısı dahil) yapmadan yayımlar; yerel durum denetimi JSON çağrısından önce yapılır; kimlik anahtarı kayıtlı Platform hedefini (normalize origin + API kökü), sürüm kimliğini, biçimi ve varsa `fold`u kapsar ve iki farklı profil/hizmet arasında aynı hedef adı/sürüm UUID’si ile kalan stage yeniden kullanılmaz; `download_busy`/`download_partial_unverified` mesajları sabittir ve dosya adı taşımaz.
5. Canlı yoklama/kabul yalnız kullanıcının erişebildiği bir model sürümü ve ayrı yetkiyle; yapılmazsa açıkça yapılmadı olarak kalır.

## Doğrulama

CLI/API integration testleri, kurulu paket yolculuğu, belge/rehber kontrolleri, Ruff, strict mypy ve yorunge-contract-change denetim listesi. Native ölçüm P02-3o’dadır.

**Gerçekleşen kapsam (P02-3n).** `application/model_download.py` (sorgu: açık biçim, `fold` yalnız verildiyse; cevap codec’i: düz nesne, iki dize, anahtar taraması, ad doğrulanıp unutulur, adres kayıtlı origin’de ve tam model önekinde), `adapters/model_download.py` (argüman yargısı → yerel snapshot → motor; `TransferSession` bir indirme için), `adapters/command_arguments.py` (sürüm komutlarıyla ortak zemin kuralları), `api.download_model_weights`, `cli/models.py` (ayrıştırıcı, metin, TTY ilerleme çizgisi) ve `cli/__init__.py` kaydı. Anlatım [referanstaki “Model ağırlığı yüzeyi (P02-3n)” bölümündedir](../../reference/download-engine.md#model-ağırlığı-yüzeyi-p02-3n). Kararlar: yerel credential snapshot’ı bir kez yakalanır ve indirmeden sonra onaylanmaz; kimlik her koşuda çözülür (tam-stage’in ağsız yayımı için bile — belgelenmiş sınır); JSON çağrısının 404’ü ayrı bir kod değildir (`remote_failed`/1: sürüm mü biçim mi yok ayırt edilemez, katalog çözümü P02-4’tedir); `fold` verilmezse hiç gönderilmez; yanıt gövdesi 1 MiB ile sınırlıdır; imzalı adrese boşluk/kontrol karakteri taşıyan cevap `invalid_response`dur. Testler: `tests/contracts/test_model_download_codec.py` (97), `tests/integration/test_model_download.py` (75, API + gerçek loopback TLS: tel üstünde anahtar yalnız JSON çağrısında, kimlik anahtarı/fold, adres ve cevap reddi hiç imzalı istek yapmadan, durum kodları, devam, ağsız tam-stage, başka hizmetin stage’i, argüman sırası, sızıntı) ve `test_model_download_cli.py` (36, gerçek süreç: yardım, çıktı kipleri, exit kodları, SIGINT ve kapalı stdout, ilerleme çizgisi). **Yapılmadı:** başlangıç yoklama kapısı ve canlı kabul (kullanıcının erişebildiği bir model sürümü ve ayrı yetki sağlanmadı; Kabul 5), kurulu paket CI satırı (P02-3b şemsiyesi).

## Teslim kaydı

Draft; kod ve çevrimdışı testler çalışma dalındadır; review ve canlı kabul kanıtı yoktur.
