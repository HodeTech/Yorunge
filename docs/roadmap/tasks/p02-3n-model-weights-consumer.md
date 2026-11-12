---
id: P02-3n
phase: P02
status: verified
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
4. Kurulu CLI yolculuğu: yardım, yanlış format, var olan hedef, yarım indirme sonrası aynı komutla devam; tam-stage bırakılmışsa komut hiçbir ağ isteği (JSON çağrısı dahil) yapmadan yayımlar; yerel durum denetimi JSON çağrısından önce yapılır; kimlik anahtarı kayıtlı Platform hedefini (normalize origin + API kökü), sürüm kimliğini, biçimi ve varsa `fold`u kapsar; başka hedeften, sürümden, biçimden ya da fold’dan kalan stage aynı hedef adıyla bile yeniden kullanılmaz (anahtar hedefe aittir: aynı hedefe başka bir anahtar/profil aynı stage’i sürdürür); `download_busy`/`download_partial_unverified` mesajları sabittir ve dosya adı taşımaz.
5. Canlı yoklama/kabul yalnız kullanıcının erişebildiği bir model sürümü ve ayrı yetkiyle; yapılmazsa açıkça yapılmadı olarak kalır.

## Doğrulama

CLI/API integration testleri, kurulu paket yolculuğu, belge/rehber kontrolleri, Ruff, strict mypy ve yorunge-contract-change denetim listesi. Native ölçüm P02-3o’dadır.

**Gerçekleşen kapsam (P02-3n).** `application/model_download.py` (sorgu: açık biçim, `fold` yalnız verildiyse; cevap codec’i: düz nesne, iki dize, anahtar taraması, ad doğrulanıp unutulur, adres kayıtlı origin’de ve tam model önekinde), `adapters/model_download.py` (argüman yargısı → yerel snapshot → motor; `TransferSession` bir indirme için), `adapters/command_arguments.py` (sürüm komutlarıyla ortak zemin kuralları), `api.download_model_weights`, `cli/models.py` (ayrıştırıcı, metin, TTY ilerleme çizgisi) ve `cli/__init__.py` kaydı. Anlatım [referanstaki “Model ağırlığı yüzeyi (P02-3n)” bölümündedir](../../reference/download-engine.md#model-ağırlığı-yüzeyi-p02-3n). Kararlar: yerel credential snapshot’ı bir kez yakalanır ve indirmeden sonra onaylanmaz; kimlik her koşuda çözülür (tam-stage’in ağsız yayımı için bile — belgelenmiş sınır); JSON çağrısının 404’ü ayrı bir kod değildir (`remote_failed`/1: sürüm mü biçim mi yok ayırt edilemez, katalog çözümü P02-4’tedir); `fold` verilmezse hiç gönderilmez; yanıt gövdesi 1 MiB ile sınırlıdır; imzalı adrese boşluk/kontrol karakteri taşıyan cevap `invalid_response`dur. R1 sonrası eklenenler: `_ADDRESS` deseni (HTTP istemcisinin telde yeniden yazacağı baytlar ve karışık harfli şema `invalid_response`), önekin kendisi/dizin/`..;x` reddi, JSON çağrısının yalnız 200’ü kabul etmesi, API’nin `int` tipleri, ilerleme yazıcısının durdurulmuş terminali beklememesi, `state_busy` için sınırlı yeniden deneme ve hata metni ipuçları (`transport_timeout`, `download_integrity_mismatch`, `download_target_invalid`, `--no-resume` ile `download_partial_unverified`). Testler: `tests/contracts/test_model_download_codec.py` (132: sorgu, önek ve cevap codec’i, her reddedilen adres/ad/alan, telde yeniden yazılan baytlar, tek nesne adlandırma, kodlanmış anahtar), `test_model_download_kills.py` (36: R1-B’nin öldürdüğü codec ve argüman yardımcısı mutantları), `test_model_download_reference.py` (4: referanstaki durum tablosu, önek, sınırlar ve çıkış kodları koda bağlı), `tests/integration/test_model_download.py` (75, API + gerçek loopback TLS: tel üstünde anahtar yalnız JSON çağrısında, kimlik anahtarı/fold, adres ve cevap reddi hiç imzalı istek yapmadan, durum kodları, devam, ağsız tam-stage, başka hizmetin stage’i, argüman sırası, sızıntı), `test_model_download_pins.py` (28: kimlik anahtarının her girdisi, `timeout`un işe girmesi, yalnız 200, API tipleri, kapanış hatasının teslim edilmiş dosyayı ezmemesi, `state_busy` yeniden denemesi, `--project`), `test_model_download_kills.py` (10) ve `test_model_download_cli.py` (39, gerçek süreç: yardım, çıktı kipleri, exit kodları, SIGINT ve kapalı stdout, ilerleme çizgisi, hata ipuçları) ile `test_model_download_cli_kills.py` (33: her seçenek tek, yazılan seçeneklerin API’ye gittiği, gerçek pty’de ilerleme çizgisi, durdurulmuş terminal). **Yapılmadı:** başlangıç yoklama kapısı ve canlı kabul (kullanıcının erişebildiği bir model sürümü ve ayrı yetki sağlanmadı; Kabul 5), kurulu paket CI satırı (P02-3b şemsiyesi).

## Teslim kaydı

- PR/commit: tek development PR’ı bu daldan açılır (bağlantı PR açıklamasındadır); adım commit’leri `feat/p02-3-dataset-recovery` dalındadır: uygulama [00a248d](https://github.com/HodeTech/Yorunge/commit/00a248df0607c331f786f24492c7ace90c5b62ec); R1 düzeltmeleri [386bae8](https://github.com/HodeTech/Yorunge/commit/386bae8de52b1c1ccef81f0097394d8d20b10d3a); R2 düzeltmeleri [9d27107](https://github.com/HodeTech/Yorunge/commit/9d271074d4699ed90c5fb15ac233add0308656f6), [4f267d6](https://github.com/HodeTech/Yorunge/commit/4f267d6d0add85228835118030c19992854ec041).
- Sonuç: `yorunge models download --version-id UUID --format onnx|pt|tflite --weights-out FILE [--fold N] [--sha256 HEX] [--timeout S] [--no-resume]` ve `api.download_model_weights`: kayıtlı Platform kimliğiyle tek JSON çağrısı, imzalı adresten kimliksiz indirme, no-clobber yayın, görünür doğrulama seviyesi (`transfer_complete` / `sha256_matched`); sıkı adres codec’i (tek nesne, telde değişmeyecek baytlar, dot-segment’siz), `state_busy` için sınırlı yeniden deneme, durdurulmuş terminali beklemeyen ilerleme çizgisi (R1 ve R2 kapandı; Adım 20). Tam paket: 12.721 geçti, 1 atlandı, 0 düştü (`1b2cc1f`, temiz klon, macOS; ilk tam paket 21 integration hatası, ilk üç CI koşusu 6 testte hata, bir admission yarış kusuru ve durum deposunda bir journal yarışı buldu, düzeltildi (açık kayıtlar araştırma kaydındadır); ayrıntı araştırma kaydındadır).
- Kalan sınır: Canlı kabul ve başlangıç yoklama kapısı **yapılmadı**: kullanıcının erişebildiği bir model sürümü ve ayrı yetki sağlanmadı (K6a); JSON şekli ve `/files/evren-models/` öneki çevrimdışı keşiften gelir, canlı doğrulanmadı; katalog/ad çözümü P02-4’tedir; ZIP ve dataset öğesi indirmesi ile `size_matched` yoktur; kurulu `models download` smoke’u P02-3z’de yerelde geçti.
