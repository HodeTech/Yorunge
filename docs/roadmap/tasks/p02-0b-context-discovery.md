---
id: P02-0b
phase: P02
status: draft
size: M
depends_on: [P02-0a, P01-2b, P01-3a, P01-5a, P01-5b]
capabilities: [C01, C02, C13]
---
# P02-0b — Hizmete bağlı gerçek context keşfi

**Tarih:** 2026-10-31. **Durum:** Taslak; ADR-0020 Proposed, raw API-key identity sözleşmesi ve canlı kabul kapısı açık. [Paket planı](../p02-0-delivery-plan.md) P02-0a ile birlikte tek nihai PR’ı ve adım/review döngüsünü taşır. Bu kartın yazılması ürün uygulaması değildir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı seçtiği hizmet/anahtarın hangi kimlik ve proje bağını gerçekten doğruladığını, hangi alanı sağlayıcının sunmadığını görür. Platform ve LLM kanıtları birbirine geçirilmez; eski profil tercihi uzak yetki sayılmaz. Mevcut Context yalnız offline tercih, credential registry yalnız yerel kimlik/nesil; public remote discovery veya trusted remote authorization resolver yoktur.

## Giren ve girmeyen kapsam

Seçili tek hizmet için açık salt okunur context keşfi, ayrı tipli sonuç, ortak CLI/Python yolu, credential snapshot/final nesil kontrolü, bounded HTTP ve açık seçim/eksik kimlik deneyimi girer. Platform aday me/org/project ve LLM terms status kapsamı [ADR-0020](../../decisions/0020-service-bound-context-discovery.md) ile onaya sunulur; candidate endpoint erişimi uygulanmış/kanıtlı değildir.

Yeni login/browser JWT fallback, hesap/key oluşturma, şart kabulü, config’e otomatik seçim yazma, generic endpoint/debug komutu, remote izin cache’i, yeni DB şeması, model/kota toplu taraması, upload/inference ve ücretli export girmez. P01 public producer draft/blocked sınırı bu salt okuma işiyle açılmaz. C01/C02’nin bütün görev/hesap kapsamı bu dar kartla tamamlanmış olmaz.

## Bağımlılıklar ve kararlar

P01 bağımlılıkları PR #6/#8/#11 ile development’da; [güncel kapanış](../../research/p01-remaining-implementation-validation.md#development-merge-kapanışı) kanıtlıdır. P02-0a’nın gerçek araştırma/review kabulü aynı dalda tamamlanmalıdır. ADR-0020 onayı, kapalı discovery referansı ve Platform API key kimlik/envelope/pagination/permission sözleşmesinin teyidi olmadan kart ready olmaz. LLM hesap/proje alanı yokluğu null/not_exposed olarak açıklanır; sağlayıcı kimliği uydurulmaz.

Canlı çağrı yetkisi/sınırı [araştırma pilot planına](../../research/p02-contract-sdk-pilot.md#küçük-pilot-planı--icra-edilmedi) göre somutlaştırılır. Salt okunur source araştırması canlı hesap yetkisi değildir. Hesap sahibinin onayı, env adları ve seçili scope henüz sağlanmadı. Geçerli sözleşme veya erişim yoksa offline test başarısı tam entegrasyon kabulüne yükseltilmez.

## Sözleşme ve uygulama sınırı

Domain/application tipli keşif ve doğrulama sonucunu sahiplenir; somut endpoint/HTTP adaptörü dış katmandadır. Yeni `ContextDiscovery` için kesin alan/tür/null/validation/error/byte/pagination biçimi ürün kodundan önce yeni canonical reference’ta yazılacaktır; henüz böyle bir public wire uygulanmadı. Eski config/Context/Plan/Result/capability kayıtları değiştirilmez. Yeni CLI/API adları ADR’de Proposed’dır; README’de çalışan örnek gibi sunulmaz.

## Kabul

1. Her hizmetin raw minimum schema/header/envelope ve liste tamlığı kanıta bağlıdır. API-key auth sözleşmesi yoksa aynı endpoint/parametrelerde strict pozitif cevap + yetkili ayrı invalid-key kontrolünde401/403 zorunludur; pozitif2xx tek başına auth bağı kurmaz. Platform principal/account/org anlamı belirsizken seçili account doğrulanmış gösterilmez. LLM exposed olmayan kimliği null/not_exposed, seçili tercihi unverified gösterir; model owner veya key hash’i hesap olmaz.
2. Explicit CLI/Python aynı kullanım senaryosunda seçilen hedef+credential ID/revision ve seçili scope’u korur. Local help/context/doctor ağ/sır/DB açmaz. Env bir kez okunur; wrong-service/fallback/browser token yoktur.
3. Gerçek TLS fixture’da 401/403/429, malformed/duplicate/nonfinite/2xx logical error, redirect/cookie/proxy/reflected secret ve geç/oversize yanıtlar kontrollü sonuç verir; API/raw provider exception/PII sızmaz. Kısa secret ve sabit mesaj çakışması P01 kuralıyla sınanır.
4. Çok/boş proje, explicit seçim, wrong-parent/absent ID, duplicate/page-loop/incomplete/128 satır/boyut sınırı bağımsız fixture ile sınanır. İlk UUID seçilmez; incomplete listede not_found/unsupported uydurulmaz. Salt görünürlük yazma izni üretmez.
5. Ağdan sonra başka süreç credential revision/reset/clock generation değiştirirse final kapı `state_changed` verir; eski gözlem verified yayımlanmaz. Toplam30 s/4 GET/8 attempt/response1 MiB/toplam4 MiB ve mevcut5 s store/1 s lock sınırları kabul edilir; iptal/cleanup fiziksel sistem I/O garantisi diye sunulmaz.
6. Yeni ayrı wire text/JSON/NDJSON eşliği, UTF-8, non-TTY promptsuz davranış, SIGINT/BrokenPipe ve önceki Context/Plan/doctor byte/semantik uyumu korunur. UX hedefi: iki hizmetli sentetik profilde ≤3 komutla doğru hizmet/explicit project durumunu bulma, yanlış hedefe0 istek; çıktı sağlayıcı alanı yokluğunu açıkça gösterir. Canlı görev süresi/yardım ayrıca kaydedilir.
7. Gerçek hizmet başına scoped read pilotu; auth kabulü, gözlenen/gözlenemeyen kimlik ve selected project eşliği ayrı raporlanır. Canlı kabul yokken veya Platform key kimlik sözleşmesi açıkken kart/P02-0 verified değildir; kapalı kimlik sahte başarıya dönmez.
8. Uygun runtime test/statik/belge/ajan, wheel+sdist iki temiz kurulum ve son kaynağa bağlı startup/jobs kapıları geçer. Adım başına iki fresh review turu, doğrulanan fix/commit ve final PR kaydı vardır; eski referans yeni source kabulü yerine kullanılmaz.

## Doğrulama

[CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi) runtime/API matrisi; hedefli unit/contract, gerçek TLS/subprocess/iki süreç SQLite yarışı, eski wire uyumu; final tam takım/build/kurulum ve seri kaynak bağlı ölçümler. Live pilot ayrı yetkili scope/limit/hata kaydıdır, CI sentetik/anahtarsız kalır. Gerçek hesap yanıtı/secret/log repoya eklenmez.

## Teslim kaydı

Henüz uygulanmadı veya teslim edilmedi. Proposed ADR onayı, kapalı raw/reference sözleşmesi ve canlı kabul koşulları açık; P02-0a araştırması P02-0b’nin bitmesi değildir. Gerçek commit/PR/test ve kalan sınır uygulama sırasında eklenecektir.
