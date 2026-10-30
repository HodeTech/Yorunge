---
id: P02-0b
phase: P02
status: draft
size: M
depends_on: [P02-0c, P02-0d]
capabilities: [C01, C02, C13]
---
# P02-0b — Hizmete bağlı gerçek context keşfi

**Tarih:** 2026-10-31. **Durum:** Üst teslim taslağı; ADR-0020 Accepted. P02-0c LLM ve P02-0d Platform hazırlık/uygulama/kabulleri bağımsız; bütünü iki kol bitince kapanır. [Paket planı](../p02-0-delivery-plan.md) P02-0a ile birlikte tek nihai PR’ı ve adım/review döngüsünü taşır. Bu kartın yazılması ürün uygulaması değildir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı seçtiği hizmet/anahtarın hangi kimlik ve proje bağını gerçekten doğruladığını, hangi alanı sağlayıcının sunmadığını görür. Platform ve LLM kanıtları birbirine geçirilmez; eski profil tercihi uzak yetki sayılmaz. Mevcut Context yalnız offline tercih, credential registry yalnız yerel kimlik/nesil; public remote discovery veya trusted remote authorization resolver yoktur.

## Giren ve girmeyen kapsam

Seçili tek hizmet için açık salt okunur context keşfi, ayrı tipli sonuç, ortak CLI/Python yolu, credential snapshot/final nesil kontrolü, bounded HTTP ve açık seçim/eksik kimlik deneyimi girer. Platform aday me/org/project ve LLM terms status kapsamı [ADR-0020](../../decisions/0020-service-bound-context-discovery.md) ile benimsendi; candidate endpoint erişimi uygulanmış/kanıtlı değildir.

Yeni login/browser JWT fallback, hesap/key oluşturma, şart kabulü, config’e otomatik seçim yazma, generic endpoint/debug komutu, remote izin cache’i, yeni DB şeması, model/kota toplu taraması, upload/inference ve ücretli export girmez. P01 public producer draft/blocked sınırı bu salt okuma işiyle açılmaz. C01/C02’nin bütün görev/hesap kapsamı bu dar kartla tamamlanmış olmaz.

## Bağımlılıklar ve kararlar

P01 bağımlılıkları PR #6/#8/#11 ile development’da ve P02-0a araştırma kabulü verified. Kullanıcı 31 Ekim review düzeltmelerinden sonra ADR-0020 kabul/uygulamasını yetkilendirdi. [P02-0c LLM](p02-0c-llm-context-discovery.md) kendi kapalı terms/reference kabulüyle Platform’dan bağımsız başlayabilir; [P02-0d Platform](p02-0d-platform-context-discovery.md) yalnız kendi raw/key/identity/envelope/pagination kapısını bekler. Bu aggregate kartı alt hizmetin kod başlangıç kapısı değildir; iki alt teslim ve live kabulleri bitmeden verified olmaz. LLM’de selected=null, profile_preference scope=unknown/not_applicable ayrımı korunur.

Canlı çağrı yetkisi/sınırı [araştırma pilot planına](../../research/p02-contract-sdk-pilot.md#küçük-pilot-planı--icra-edilmedi) göre somutlaştırılır. Salt okunur source araştırması canlı hesap yetkisi değildir. Kullanıcı hesabı/env’yi henüz hazırlamadığını bildirdi; [yerel hazırlık yönergesi](../../p02-account-setup.md) verildi. Bu live kabul dış koşulu LLM offline implementasyonunu durdurmaz. Geçerli sözleşme veya erişim yoksa offline test başarısı tam entegrasyon kabulüne yükseltilmez.

## Sözleşme ve uygulama sınırı

Domain/application tipli keşif ve doğrulama sonucunu sahiplenir; somut endpoint/HTTP adaptörü dış katmandadır. Kesin LLM alan/tür/null/validation/error/byte ve pilot kapsamı [ContextDiscovery v1 referansındadır](../../reference/context-discovery.md); ürün uygulanmışlığı ayrıca gösterilir. Platform varyantı raw sözleşme kapanmadan uydurulmaz. Eski config/Context/Plan/Result/capability kayıtları değiştirilmez. Yeni CLI/API adları Accepted tasarımdır; README’de çalışan örnek gibi sunulmaz.

## Kabul

1. Her hizmetin raw minimum schema/header/envelope ve liste tamlığı kanıta bağlıdır. API-key auth sözleşmesi yoksa her endpoint/parametre/hedef için ayrı iyi biçimli random kontrol; 401 veya anlamı kapanmış invalid-key403 gerekir, malformed/terms/permission403 yeterli değildir. Pozitif 2xx tek başına auth bağı kurmaz. Platform principal/account/org anlamı belirsizken seçili account doğrulanmış gösterilmez. LLM exposed olmayan kimliği null/not_exposed, selected account/project=null, ham profil tercihini profile_preference scope unknown/not_applicable gösterir; model owner veya key hash’i hesap olmaz.
2. Explicit CLI/Python aynı kullanım senaryosunda seçilen hedef+credential ID/revision ve seçili scope’u korur. Local help/context/doctor ağ/sır/DB açmaz. Env bir kez okunur; wrong-service/fallback/browser token yoktur.
3. Gerçek TLS fixture’da 401/403/429, malformed/duplicate/nonfinite/2xx logical error, redirect/cookie/proxy/reflected secret ve geç/oversize yanıtlar kontrollü sonuç verir; API/raw provider exception/PII sızmaz. Kısa secret ve sabit mesaj çakışması P01 kuralıyla sınanır.
4. Çok/boş proje, explicit seçim, wrong-parent/absent ID, duplicate/page-loop/incomplete/128 satır/boyut sınırı bağımsız fixture ile sınanır. Me/list404 invalid_response, detail404 selected_project_not_found/selection_unverified; değişen üyelik/sayfa fixture’ları vardır. İlk UUID seçilmez; incomplete listede not_found/unsupported uydurulmaz. Salt görünürlük yazma izni üretmez.
5. Ağdan sonra başka süreç credential revision/reset/clock generation değiştirirse final kapı `state_changed` verir; eski gözlem verified yayımlanmaz. Normal Platform 4 GET/8 attempt/4 MiB; LLM 1 GET/2 attempt/1 MiB; hizmet başına toplam 30 s, response 1 MiB ve mevcut 5 s store/1 s lock sınırları kabul edilir; iptal/cleanup fiziksel sistem I/O garantisi diye sunulmaz.
6. Yeni ayrı wire text/JSON/NDJSON eşliği, UTF-8, non-TTY promptsuz davranış, SIGINT/BrokenPipe ve önceki Context/Plan/doctor byte/semantik uyumu korunur. UX hedefi: iki hizmetli sentetik profilde ≤3 komutla doğru hizmet/explicit project durumunu bulma, yanlış hedefe0 istek; çıktı sağlayıcı alanı yokluğunu açıkça gösterir. Canlı görev süresi/yardım ayrıca kaydedilir.
7. Gerçek hizmet başına scoped read pilotu; auth kabulü, gözlenen/gözlenemeyen kimlik ve selected project eşliği ayrı raporlanır. Canlı kabul yokken veya Platform key kimlik sözleşmesi açıkken kart/P02-0 verified değildir; kapalı kimlik sahte başarıya dönmez.
8. Uygun runtime test/statik/belge/ajan, wheel+sdist iki temiz kurulum ve son kaynağa bağlı startup/jobs kapıları geçer. Adım başına iki fresh review turu, doğrulanan fix/commit ve final PR kaydı vardır; eski referans yeni source kabulü yerine kullanılmaz.

## Doğrulama

[CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi) runtime/API matrisi; hedefli unit/contract, gerçek TLS/subprocess/iki süreç SQLite yarışı, eski wire uyumu; final tam takım/build/kurulum ve seri kaynak bağlı ölçümler. Live pilot ayrı yetkili scope/limit/hata kaydıdır, CI sentetik/anahtarsız kalır. Gerçek hesap yanıtı/secret/log repoya eklenmez.

## Teslim kaydı

Henüz uygulanmadı veya teslim edilmedi. ADR Accepted; bağımsız hizmet kartlarının kapalı raw/reference ve canlı kabul koşulları ayrı; P02-0a araştırması P02-0b’nin bitmesi değildir. Gerçek commit/PR/test ve kalan sınır uygulama sırasında eklenecektir.
