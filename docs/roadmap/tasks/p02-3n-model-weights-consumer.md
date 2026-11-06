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

P02-3m verified olmalıdır; Platform bağlamı P02-0d’dedir. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md)’nin Accepted olması gerekir (bugün Proposed). Yoklama kapısı P02-3j öncesinde yapılır; kullanıcının erişebildiği bir model sürümü kimliği ve ayrı yetki gerekir, yoksa kapı “yoklama yapılmadı” olarak kayda geçer. CLI/API için yorunge-contract-change disiplini uygulanır.

## Sözleşme ve uygulama sınırı

[indirme motoru sözleşmesi](../../reference/download-engine.md) içindeki yüzey. JSON çağrısı yalnız kayıtlı Platform kimliğiyle ve ADR-0017 salt okuma politikasıyla yapılır; `download_url` kayıtlı Platform origin’inde ve tam olarak `{api_base_path}/files/evren-models/` önekinde (yanıt genişletemez), https/443, userinfo/fragment/dot-segment olmadan ve ≤16 KiB olmalıdır; sağlayıcının `filename` alanı çıktı adı olmaz. Beklenen özet yalnız kullanıcının `--sha256` değeridir. Erişim/lisans/şart engeli `remote_access_denied`/3’tür ve şartlar kabul edilmez.

## Kabul

1. Loopback TLS: JSON çağrısı `X-API-Key` taşır, indirme taşımaz; yanlış origin, önek (başka bucket dahil), http, userinfo, fragment, `..`, aşırı URL, eksik/yanlış tipli alan, sağlayıcı filename’inin yol ayırıcı içermesi ve 401/403/404/429/5xx hepsi imzalı URL isteğine geçmeden kontrollü ret verir (`{api_base_path}/files/` dataset bucket yolu ve API tabanı olmayan `/files/evren-models/` dahil); `fold` verilirse iletilir ve kimlik anahtarına girer.
2. `--sha256` eşleşirse `sha256_matched`/`user_supplied`, yoksa `transfer_complete`; uyuşmazlık exit 7 ve hedef yok; seviye çıktıda doğru ve fazla iddiasız; `--fold`, `--timeout`, `--sha256` değer alanları strict doğrulanır.
3. JSON/NDJSON saf, TTY ilerleme yalnız stderr, BrokenPipe/SIGINT/Task.cancel mevcut 6/1/6 ve ID önceliği; sentinel testleri imzalı URL/query/ETag/filename sızıntısı olmadığını gösterir.
4. Kurulu CLI yolculuğu: yardım, yanlış format, var olan hedef, yarım indirme sonrası aynı komutla devam; tam-stage bırakılmışsa komut hiçbir ağ isteği (JSON çağrısı dahil) yapmadan yayımlar; yerel durum denetimi JSON çağrısından önce yapılır; `download_busy`/`download_partial_unverified` mesajları sabittir ve dosya adı taşımaz.
5. Canlı yoklama/kabul yalnız kullanıcının erişebildiği bir model sürümü ve ayrı yetkiyle; yapılmazsa açıkça yapılmadı olarak kalır.

## Doğrulama

CLI/API integration testleri, kurulu paket yolculuğu, belge/rehber kontrolleri, Ruff, strict mypy ve yorunge-contract-change denetim listesi. Native ölçüm P02-3o’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
